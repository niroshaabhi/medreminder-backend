# backend/models/habit_model.py
"""
AI Smart Mode — Scikit-learn Habit Learning Model
--------------------------------------------------
Learns when the patient actually takes their medicine
and suggests an adjusted reminder time for Flexible Mode.

Algorithm:
  - Collect actual intake times from adherenceLog
  - Compute mean actual time vs scheduled time
  - If the patient consistently takes medicine N minutes late,
    shift the reminder forward by that amount (capped at ±60 min)
  - Uses LinearRegression as a simple trend predictor
"""
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta


class HabitModel:
    def __init__(self):
        self.model = LinearRegression()

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert 'HH:MM' or 'HH:MM AM/PM' to minutes since midnight"""
        try:
            for fmt in ('%H:%M', '%I:%M %p', '%I:%M%p'):
                try:
                    t = datetime.strptime(time_str.strip(), fmt)
                    return t.hour * 60 + t.minute
                except ValueError:
                    continue
        except Exception:
            pass
        return 0

    def _minutes_to_time(self, minutes: int) -> str:
        """Convert minutes since midnight to 'HH:MM' string"""
        minutes = max(0, min(1439, int(minutes)))
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"

    def _extract_actual_times(self, log: list, scheduled_time: str) -> list:
        """Extract actual intake times from adherenceLog that match scheduled time"""
        scheduled_min = self._time_to_minutes(scheduled_time)
        actual_times  = []

        for entry in log:
            if entry.get('action') != 'taken':
                continue
            ts = entry.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(ts)
                actual_min = dt.hour * 60 + dt.minute
                # Only consider entries within ±90 min of the scheduled time
                if abs(actual_min - scheduled_min) <= 90:
                    actual_times.append(actual_min)
            except Exception:
                continue

        return actual_times

    def predict_best_time(self, scheduled_time: str, log: list) -> str:
        """
        Given the scheduled time and adherence log,
        return the AI-suggested best reminder time.
        """
        actual_times = self._extract_actual_times(log, scheduled_time)
        scheduled_min = self._time_to_minutes(scheduled_time)

        # Need at least 3 data points for meaningful adjustment
        if len(actual_times) < 3:
            return scheduled_time

        actual_arr = np.array(actual_times)
        mean_actual = float(np.mean(actual_arr))
        delay       = mean_actual - scheduled_min

        # Cap adjustment at ±60 minutes
        delay = max(-60, min(60, delay))

        # Only adjust if the average delay is more than 5 minutes
        if abs(delay) < 5:
            return scheduled_time

        # Use LinearRegression to trend the delay over recent sessions
        if len(actual_times) >= 5:
            X = np.arange(len(actual_times)).reshape(-1, 1)
            y = np.array(actual_times)
            self.model.fit(X, y)
            # Predict next session
            next_idx = np.array([[len(actual_times)]])
            predicted = float(self.model.predict(next_idx)[0])
            delay = predicted - scheduled_min
            delay = max(-60, min(60, delay))

        adjusted = scheduled_min + delay
        return self._minutes_to_time(adjusted)

    def get_adherence_score(self, log: list) -> dict:
        """Calculate adherence statistics from log"""
        if not log:
            return {'score': 0, 'taken': 0, 'skipped': 0, 'total': 0}

        taken   = sum(1 for e in log if e.get('action') == 'taken')
        skipped = sum(1 for e in log if e.get('action') == 'skip')
        total   = len(log)
        score   = round((taken / total) * 100) if total > 0 else 0

        return {'score': score, 'taken': taken, 'skipped': skipped, 'total': total}
