import time
from pymavlink import mavutil
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
import threading


class MavlinkTelemeter:
    def __init__(self, connection_string):
        self.master = mavutil.mavlink_connection(connection_string)
        self.master.wait_heartbeat()
        print("Heartbeat from system (system %u component %u)" % (
            self.master.target_system, self.master.target_component))

        self.telemetry = {
            'speed': 0,
            'altitude': 0,
            'heading': 0,
            'pitch': 0,
            'roll': 0,
            'battery': 0,
            'mAhUsed': 0,
            'mAhPerKm': 0,
            'latitude': 0,
            'longitude': 0,
            'distanceToHome': 0,
            'headingToHome': 0,
            'timestamp': "2021-01-01T00:00:00Z",
            'amps': 0,
            'coveredDistance': 0,
            'flightTime': "00:00:00",
            'armed': False,
            'flightMode': ""
        }

        self.mah_per_km_history = []

        self.last_telemetry = self.telemetry.copy()
        self.start_time = time.time()
        self.start_position = None
        self.last_position = None
        self.last_mah_used = 0
        self.last_distance = 0
        self.last_update_time = time.time()

        self.telemetry_changed = threading.Event()

        thread = threading.Thread(target=self.loop_update, daemon=True)
        thread.start()
        thread = threading.Thread(target=self.vfr_hud_update, daemon=True)
        thread.start()
        thread = threading.Thread(target=self.attitude_update, daemon=True)
        thread.start()

        thread = threading.Thread(target=self.loop_interval_msg, daemon=True)
        thread.start()

    def loop_interval_msg(self):
        while True:
            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD, 30_000)
            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE, 30_000)

            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 100_000)
            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_BATTERY_STATUS, 100_000)
            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_HOME_POSITION, 100_000)
            self.set_message_interval(mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT, 100_000)
            time.sleep(1)

    def set_message_interval(self, message_id, interval_us):
        self.master.mav.command_long_send(
            self.master.target_system, self.master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,  # confirmation
            message_id,  # param1: Message ID
            interval_us,  # param2: Interval in microseconds
            0, 0, 0, 0,  # param3-6: Unused
            0  # param7: Response target (0: Flight-stack default)
        )

        # Wait for the command to be acknowledged
        self.master.recv_match(type='COMMAND_ACK', blocking=False, timeout=5)

    def loop_update(self):
        while True:
            self.update()

    def vfr_hud_update(self):
        while True:
            msg = self.master.recv_match(type='VFR_HUD', blocking=True)
            if msg:
                self.telemetry['speed'] = msg.groundspeed
                self.telemetry['heading'] = msg.heading
                # self.telemetry_changed.set()

    def attitude_update(self):
        while True:
            msg = self.master.recv_match(type='ATTITUDE', blocking=True)
            if msg:
                self.telemetry['pitch'] = msg.pitch * 180 / 3.14159
                self.telemetry['roll'] = msg.roll * 180 / 3.14159
                self.telemetry_changed.set()

    def update(self):
        msg = self.master.recv_match(type=["GLOBAL_POSITION_INT", "BATTERY_STATUS",
                                           "HOME_POSITION", "HEARTBEAT"], blocking=True, timeout=0.04)
        if msg:
            changed = True
            if msg.get_type() == 'VFR_HUD':
                self.telemetry['speed'] = msg.groundspeed
                self.telemetry['heading'] = msg.heading
            elif msg.get_type() == 'ATTITUDE':
                self.telemetry['pitch'] = msg.pitch * 180 / 3.14159  # radians to degrees
                self.telemetry['roll'] = msg.roll * 180 / 3.14159  # radians to degrees
            elif msg.get_type() == 'GLOBAL_POSITION_INT':
                self.telemetry['altitude'] = msg.relative_alt / 1000  # mm to m
                self.telemetry['latitude'] = msg.lat / 1e7
                self.telemetry['longitude'] = msg.lon / 1e7
                self.update_distance()
                if self.start_position:
                    current_pos = (self.telemetry['latitude'], self.telemetry['longitude'])
                    self.telemetry['distanceToHome'] = self.haversine(self.start_position, current_pos)
                    self.telemetry['headingToHome'] = self.calculate_heading(current_pos, self.start_position)
            if msg.get_type() == 'BATTERY_STATUS':
                self.telemetry['battery'] = msg.voltages[0] / 1000  # mV to V
                self.telemetry['mAhUsed'] = msg.current_consumed
                self.telemetry['amps'] = msg.current_battery / 100  # cA to A
                self.update_mah_per_km()
            elif msg.get_type() == 'HOME_POSITION':
                if self.start_position is None:
                    self.start_position = (msg.latitude / 1e7, msg.longitude / 1e7)
            elif msg.get_type() == 'HEARTBEAT':
                self.telemetry['armed'] = msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED == 128
                self.telemetry['flightMode'] = mavutil.mode_string_v10(msg)

                if self.telemetry['armed'] and self.start_time == 0:
                    self.start_time = time.time()
                elif not self.telemetry['armed'] and self.start_time > 0:
                    self.start_time = 0

                flight_time = time.time() - self.start_time if self.start_time > 0 else 0

                self.telemetry['flightTime'] = str(timedelta(seconds=int(flight_time)))
                self.telemetry['timestamp'] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                changed = False

            # if changed:
            #     self.telemetry_changed.set()

    def update_distance(self):
        current_pos = (self.telemetry['latitude'], self.telemetry['longitude'])
        if self.last_position:
            distance = self.haversine(self.last_position, current_pos)
            self.telemetry['coveredDistance'] += distance
        self.last_position = current_pos

    def update_mah_per_km(self):
        current_time = time.time()
        time_diff = current_time - self.last_update_time

        if time_diff > 0:
            mah_diff = self.telemetry['mAhUsed'] - self.last_mah_used
            distance_diff = self.telemetry['coveredDistance'] - self.last_distance

            if distance_diff > 0 and mah_diff > 0:
                current_mah_per_km = mah_diff / distance_diff  # Calculate current mAh/km

                # Add the current value to the history
                self.mah_per_km_history.append(current_mah_per_km)

                # Keep only the last 20 values
                if len(self.mah_per_km_history) > 20:
                    self.mah_per_km_history = self.mah_per_km_history[-20:]

                # Calculate the average of the last 20 values
                if self.mah_per_km_history:
                    self.telemetry['mAhPerKm'] = sum(self.mah_per_km_history) / len(self.mah_per_km_history)
                else:
                    self.telemetry['mAhPerKm'] = 0

            self.last_mah_used = self.telemetry['mAhUsed']
            self.last_distance = self.telemetry['coveredDistance']
            self.last_update_time = current_time

    def has_changed(self):
        changed = self.telemetry != self.last_telemetry
        self.last_telemetry = self.telemetry.copy()
        return changed

    @staticmethod
    def haversine(pos1, pos2):
        R = 6371  # Earth radius in kilometers

        lat1, lon1 = radians(pos1[0]), radians(pos1[1])
        lat2, lon2 = radians(pos2[0]), radians(pos2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    @staticmethod
    def calculate_heading(pos1, pos2):
        lat1, lon1 = radians(pos1[0]), radians(pos1[1])
        lat2, lon2 = radians(pos2[0]), radians(pos2[1])

        dlon = lon2 - lon1

        y = sin(dlon) * cos(lat2)
        x = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(dlon)
        heading = atan2(y, x)

        return (heading * 180 / 3.14159 + 360) % 360
