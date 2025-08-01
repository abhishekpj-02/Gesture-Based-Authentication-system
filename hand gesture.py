import cv2
import mediapipe as mp
import sqlite3
import time
import threading
import os
import ttkbootstrap as tb
from tkinter import ttk
from tkinter import messagebox
from PIL import Image, ImageTk
import itertools
import traceback  # Import traceback for detailed error logging

class GestureAuthentication:
    def __init__(self):
        try:
            self.conn, self.cursor = self.connect_database()
            self.cap = self.open_camera()
            self.last_logged_gesture = None
            self.last_logged_time = 0
            self.cooldown_time = 2
            self.gesture_delay = 1  # Time in seconds to wait after recognizing each gesture
            self.last_gesture_time = 0  # Timestamp of the last recognized gesture

            # Initialize MediaPipe Hands
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.8)
            self.mp_draw = mp.solutions.drawing_utils

            # Define profiles with gesture sequences
            self.profiles = {
                "Abhishek": ["Open Palm", "Peace", "Fist"],
                "Noel": ["Fist", "Open Palm", "Peace"],
                "Govind": ["Call Me", "Rock On", "Peace"]
            }
            self.captured_sequence = []
            self.sequence_timeout = 10  # Time in seconds to complete the sequence
            self.sequence_start_time = None

            self.root = tb.Window(themename="superhero")
            self.setup_gui()
            self.start_animations()

            if self.cap:
                self.update_frame()
                self.fetch_logs()

            self.root.mainloop()
        except Exception as e:
            print(f"Initialization Error: {e}")
            messagebox.showerror("Initialization Error", f"Error during initialization: {e}")
        finally:
            self.cleanup()

    def connect_database(self):
        try:
            conn = sqlite3.connect("auth_logs.db", check_same_thread=False)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS logs (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                timestamp TEXT,
                                profile TEXT,
                                gesture TEXT,
                                result TEXT)''')
            # Check if the profile column exists, if not, add it
            cursor.execute("PRAGMA table_info(logs)")
            columns = [column[1] for column in cursor.fetchall()]
            if "profile" not in columns:
                cursor.execute("ALTER TABLE logs ADD COLUMN profile TEXT")
                conn.commit()
            return conn, cursor
        except sqlite3.Error as e:
            print(f"Database Error: {e}")
            messagebox.showerror("Database Error", f"Unable to connect to the database: {e}")
            return None, None

    def open_camera(self):
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("Error: Unable to open camera")
                messagebox.showerror("Camera Error", "Unable to access the camera.")
                return None
            return cap
        except Exception as e:
            print(f"Camera Error: {e}")
            messagebox.showerror("Camera Error", f"Error accessing the camera: {e}")
            return None

    def start_animations(self):
        threading.Thread(target=self.animate_logo, daemon=True).start()

    def animate_logo(self):
        animation = itertools.cycle(["|", "/", "-", "\\"])
        while True:
            self.status_label.config(text=f"Waiting for gesture... {next(animation)}")
            time.sleep(0.3)

    def log_attempt(self, profile, gesture, result):
        try:
            current_time = time.time()
            if gesture != self.last_logged_gesture or (current_time - self.last_logged_time > self.cooldown_time):
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute("INSERT INTO logs (timestamp, profile, gesture, result) VALUES (?, ?, ?, ?)", (timestamp, profile, gesture, result))
                self.conn.commit()

                self.last_logged_gesture = gesture
                self.last_logged_time = current_time

                self.status_label.config(text=result, bootstyle="success" if "Successful" in result else "danger")
                self.fetch_logs()
        except Exception as e:
            print(f"Logging Error: {e}")
            messagebox.showerror("Logging Error", f"Error logging the attempt: {e}")

    def recognize_gesture(self, hand_landmarks):
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]
        thumb_ip = hand_landmarks.landmark[3]  # Define thumb_ip
        thumb_base = hand_landmarks.landmark[2]
        wrist = hand_landmarks.landmark[0]

        # "OK" Gesture
        if (abs(thumb_tip.x - index_tip.x) < 0.05 and 
            abs(thumb_tip.y - index_tip.y) < 0.05 and 
            thumb_tip.y < index_tip.y and
            middle_tip.y > index_tip.y and
            ring_tip.y > index_tip.y and
            pinky_tip.y > index_tip.y):  
            return "OK"

        # "Fist" Gesture
        if (index_tip.y > hand_landmarks.landmark[6].y and
            middle_tip.y > hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y > hand_landmarks.landmark[18].y):
            return "Fist"

        # "Peace" Gesture (Index & Middle fingers up, others down)
        if (index_tip.y < hand_landmarks.landmark[6].y and
            middle_tip.y < hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y > hand_landmarks.landmark[18].y):
            return "Peace"

        # "Open Palm" Gesture (All fingers up)
        if (index_tip.y < hand_landmarks.landmark[6].y and
            middle_tip.y < hand_landmarks.landmark[10].y and
            ring_tip.y < hand_landmarks.landmark[14].y and
            pinky_tip.y < hand_landmarks.landmark[18].y):
            return "Open Palm"

        # "Thumbs Up" Gesture
        if (thumb_tip.y < thumb_ip.y and
            thumb_tip.y < index_tip.y and
            thumb_tip.y < middle_tip.y and
            thumb_tip.y < ring_tip.y and
            thumb_tip.y < pinky_tip.y and
            index_tip.y > wrist.y and
            middle_tip.y > wrist.y and
            ring_tip.y > wrist.y and
            pinky_tip.y > wrist.y):
            return "Thumbs Up"

        # "Thumbs Down" Gesture
        if (thumb_tip.y > thumb_ip.y and
            thumb_tip.y > index_tip.y and
            thumb_tip.y > middle_tip.y and
            thumb_tip.y > ring_tip.y and
            thumb_tip.y > pinky_tip.y and
            index_tip.y < wrist.y and
            middle_tip.y < wrist.y and
            ring_tip.y < wrist.y and
            pinky_tip.y < wrist.y):
            return "Thumbs Down"

        # "Rock On" Gesture
        if (index_tip.y < hand_landmarks.landmark[6].y and
            middle_tip.y > hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y < hand_landmarks.landmark[18].y):
            return "Rock On"

        # "Call Me" Gesture
        if (thumb_tip.y < hand_landmarks.landmark[3].y and
            index_tip.y > hand_landmarks.landmark[6].y and
            middle_tip.y > hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y < hand_landmarks.landmark[18].y):
            return "Call Me"

        # "Victory" Gesture (Index & Middle fingers up, palm outward)
        if (index_tip.y < hand_landmarks.landmark[6].y and
            middle_tip.y < hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y > hand_landmarks.landmark[18].y and
            thumb_tip.x < hand_landmarks.landmark[2].x):
            return "Victory"

        # "Hang Loose" Gesture (Shaka sign)
        if (thumb_tip.y < hand_landmarks.landmark[3].y and
            index_tip.y > hand_landmarks.landmark[6].y and
            middle_tip.y > hand_landmarks.landmark[10].y and
            ring_tip.y > hand_landmarks.landmark[14].y and
            pinky_tip.y < hand_landmarks.landmark[18].y):
            return "Hang Loose"

        # "Stop" Gesture (Hand raised, palm facing the camera)
        if (index_tip.y < hand_landmarks.landmark[6].y and
            middle_tip.y < hand_landmarks.landmark[10].y and
            ring_tip.y < hand_landmarks.landmark[14].y and
            pinky_tip.y < hand_landmarks.landmark[18].y and
            thumb_tip.y < hand_landmarks.landmark[3].y):
            return "Stop"

        return None

    def validate_sequence(self):
        for profile, sequence in self.profiles.items():
            if self.captured_sequence == sequence:
                return profile, "Authentication Successful", (0, 255, 0)
        return None, "Access Denied", (0, 0, 255)

    def update_frame(self):
        try:
            ret, frame = self.cap.read()
            frame = cv2.flip(frame, 1)
            if not ret:
                return

            start_time = time.time()
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands.process(rgb_frame)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    self.mp_draw.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                    gesture = self.recognize_gesture(hand_landmarks)
                    result_text = ""
                    color = (255, 255, 255)

                    current_time = time.time()
                    if gesture and (current_time - self.last_gesture_time > self.gesture_delay):
                        print(f"Gesture recognized: {gesture}")  # Debug statement
                        if not self.sequence_start_time:
                            self.sequence_start_time = time.time()
                        self.captured_sequence.append(gesture)
                        self.captured_sequence = self.captured_sequence[-len(max(self.profiles.values(), key=len)):]
                        profile, result_text, color = self.validate_sequence()
                        if result_text == "Authentication Successful" or time.time() - self.sequence_start_time > self.sequence_timeout:
                            self.log_attempt(profile if profile else "Unknown", ' -> '.join(self.captured_sequence), result_text)
                            self.captured_sequence.clear()
                            self.sequence_start_time = None
                        
                        print(f"Captured sequence: {self.captured_sequence}")  # Debug statement
                        self.last_gesture_time = current_time  # Update last gesture time

                    cv2.putText(frame, result_text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)

            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            fps = int(1 / (time.time() - start_time))
            self.fps_label.config(text=f"FPS: {fps}")

            self.video_label.after(10, self.update_frame)
        except Exception as e:
            error_message = traceback.format_exc()  # Capture detailed error message
            print(f"Frame Update Error: {error_message}")
            messagebox.showerror("Frame Update Error", f"Error updating the frame: {error_message}")

    def fetch_logs(self):
        try:
            conn = sqlite3.connect("auth_logs.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM logs ORDER BY id DESC")
            rows = cursor.fetchall()

            for row in self.tree.get_children():
                self.tree.delete(row)

            for row in rows:
                self.tree.insert("", "end", values=row)
            conn.close()
        except Exception as e:
            print(f"Fetch Logs Error: {e}")
            messagebox.showerror("Fetch Logs Error", f"Error fetching logs: {e}")

    def clear_logs(self):
        try:
            conn = sqlite3.connect("auth_logs.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM logs")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='logs'")
            conn.commit()
            conn.close()
            self.fetch_logs()
        except Exception as e:
            print(f"Clear Logs Error: {e}")
            messagebox.showerror("Clear Logs Error", f"Error clearing logs: {e}")

    def show_tutorial(self):
        try:
            tutorial_window = tb.Toplevel(self.root)
            tutorial_window.title("Gesture Tutorial")
            tutorial_window.geometry("600x400")

            tb.Label(tutorial_window, text="Gesture Tutorial", font=("Arial", 16, "bold")).pack(pady=10)
            tb.Label(tutorial_window, text="1. OK Gesture: Thumb and index finger touch.\n2. Fist Gesture: Close your fist.\n3. Peace Gesture: Index and middle fingers up.\n4. Open Palm Gesture: All fingers extended.\n5. Thumbs Up Gesture: Thumb extended upwards.\n6. Thumbs Down Gesture: Thumb extended downwards.\n7. Rock On Gesture: Index and pinky fingers extended.\n8. Call Me Gesture: Thumb and pinky fingers extended.\n9. Victory Gesture: Index and middle fingers extended, palm outward.\n10. Hang Loose Gesture: Thumb and pinky fingers extended (Shaka sign).\n11. Stop Gesture: Hand raised, palm facing the camera.", 
                    font=("Arial", 14), justify="left").pack(pady=20)

            tb.Button(tutorial_window, text="Close", command=tutorial_window.destroy, bootstyle="primary").pack(pady=10)
        except Exception as e:
            print(f"Show Tutorial Error: {e}")
            messagebox.showerror("Show Tutorial Error", f"Error showing tutorial: {e}")

    def setup_gui(self):
        try:
            self.root.title("Gesture-Based Authentication")
            self.root.geometry("1200x700")

            # Video Frame
            video_frame = tb.Frame(self.root)
            video_frame.pack(side="left", padx=10, pady=10)

            self.video_label = tb.Label(video_frame)
            self.video_label.pack()

            self.fps_label = tb.Label(video_frame, text="FPS: --", font=("Arial", 12))
            self.fps_label.pack(pady=5)

            # Gesture Status Panel
            self.status_label = tb.Label(self.root, text="Waiting for gesture...", font=("Arial", 14, "bold"), bootstyle="warning")
            self.status_label.pack(pady=10)

            # Logs Frame
            logs_frame = tb.Frame(self.root)
            logs_frame.pack(side="right", padx=10, pady=10)

            tb.Label(logs_frame, text="Authentication Logs", font=("Arial", 14, "bold")).pack()

            # Table
            columns = ("ID", "Timestamp", "Profile", "Gesture", "Result")
            self.tree = ttk.Treeview(logs_frame, columns=columns, show="headings")

            # Adjust column widths dynamically
            self.tree.heading("ID", text="ID")
            self.tree.column("ID", width=40, anchor="center")

            self.tree.heading("Timestamp", text="Timestamp")
            self.tree.column("Timestamp", width=180, anchor="center")

            self.tree.heading("Profile", text="Profile")
            self.tree.column("Profile", width=100, anchor="center")

            self.tree.heading("Gesture", text="Gesture")
            self.tree.column("Gesture", width=100, anchor="center")

            self.tree.heading("Result", text="Result")
            self.tree.column("Result", width=100, anchor="center")

            self.tree.pack(expand=True, fill="both")

            # Buttons
            button_frame = tb.Frame(logs_frame)
            button_frame.pack(pady=10)

            tb.Button(button_frame, text="Clear Logs", bootstyle="danger", command=self.clear_logs).pack(side="left", padx=5)
            tb.Button(button_frame, text="Show Tutorial", bootstyle="info", command=self.show_tutorial).pack(side="left", padx=5)
        except Exception as e:
            print(f"Setup GUI Error: {e}")
            messagebox.showerror("Setup GUI Error", f"Error setting up GUI: {e}")

    def cleanup(self):
        try:
            if self.cap:
                self.cap.release()
            cv2.destroyAllWindows()
            self.conn.close()
        except Exception as e:
            print(f"Cleanup Error: {e}")
            messagebox.showerror("Cleanup Error", f"Error during cleanup: {e}")

if __name__ == "__main__":
    GestureAuthentication()