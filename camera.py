import os
import shutil
import cv2
import hashlib
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.app import App
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.label import Label
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.filemanager import MDFileManager
from kivymd.toast import toast
import psycopg2
import requests
import base64
from kivy.uix.image import Image as KivyImage
from kivy.core.image import Image as CoreImage

# PostgreSQL credentials
DB_NAME = "kivymmd_face_login"
DB_USER = "postgres"
DB_PASSWORD = "admin"
DB_HOST = "localhost"
DB_PORT = "5432"

# Directory to save uploaded images
UPLOAD_DIR = os.path.join(os.getcwd(), 'uploads')

# Ensure the 'uploads' directory exists
if not os.path.exists(UPLOAD_DIR):
	os.makedirs(UPLOAD_DIR)

class CameraWindow(Screen):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

		# Image widget for displaying camera feed
		self.camera_feed = Image(size_hint=(1, 0.5))  # Resize the window to 50% height
		layout.add_widget(self.camera_feed)

		# Create the form below the video window
		form_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

		# Email input box
		self.email_input = MDTextField(
			hint_text="Enter Email",
			size_hint=(1, None),
			height=50
		)
		form_layout.add_widget(self.email_input)

		# Password input box
		self.password_input = MDTextField(
			hint_text="Enter Password",
			password=True,  # Hide password input
			size_hint=(1, None),
			height=50
		)
		form_layout.add_widget(self.password_input)

		# Submit button
		self.submit_button = MDRaisedButton(
			text="Submit",
			size_hint=(1, None),
			height=50,
			on_press=self.on_submit
		)
		form_layout.add_widget(self.submit_button)

		# Hyperlink for new user registration
		self.register_link = Label(
			text="[ref=register]New User? Register first[/ref]",
			markup=True,
			size_hint=(1, None),
			height=50,
			color=(0, 0, 1, 1)  # Blue color for the link
		)
		self.register_link.bind(on_ref_press=self.go_to_registration)
		form_layout.add_widget(self.register_link)

		layout.add_widget(form_layout)
		self.add_widget(layout)

		# Access the device's camera (0 for the default camera)
		self.capture = cv2.VideoCapture(0)
		Clock.schedule_interval(self.update, 1.0 / 30.0)  # Update the video feed 30 times per second

	def update(self, dt):
		ret, frame = self.capture.read()
		if ret:
			# Convert the frame to texture for displaying on Kivy's Image widget
			buffer = cv2.flip(frame, 0).tobytes()
			texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
			texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
			self.camera_feed.texture = texture

	def on_submit(self, instance):
		email = self.email_input.text
		password = self.password_input.text

		# Convert the frame to base64
		ret, frame = self.capture.read()
		if ret:
			_, buffer = cv2.imencode('.jpg', frame)
			encoded_frame = base64.b64encode(buffer).decode('utf-8')

			# Send the frame and check profile existence on submit
			try:
				response = requests.post('http://localhost:5000/recognize_face', json={'image': encoded_frame})
				if response.status_code == 200:
					result = response.json()
					if result.get('match'):
						profile_info = result.get('profile')
						if profile_info:
							print('Profile Information:', profile_info)
							toast("Profile found! Redirecting...")
							
							# Pass the email to load_profile method
							self.manager.get_screen('profile').load_profile(profile_info.get('email'))
							self.manager.current = 'profile'
					else:
						toast("No matching profile found.")
				else:
					toast("Error with the backend service.")
			except Exception as e:
				print(f"Error: {e}")
				toast("Error communicating with backend.")


	def go_to_registration(self, instance, value):
		self.manager.current = 'register'

	def on_stop(self):
		# Release the camera when the app is closed
		self.capture.release()

class RegistrationWindow(Screen):
	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

		# Registration form fields
		self.name_input = MDTextField(hint_text="Name", size_hint=(1, None), height=50)
		self.email_input = MDTextField(hint_text="Email", size_hint=(1, None), height=50)
		self.mobile_input = MDTextField(hint_text="Mobile Number", size_hint=(1, None), height=50)
		self.designation_input = MDTextField(hint_text="Designation", size_hint=(1, None), height=50)
		self.emp_code_input = MDTextField(hint_text="Employee Code", size_hint=(1, None), height=50)
		self.password_input = MDTextField(hint_text="Password", password=True, size_hint=(1, None), height=50)

		# Upload button for profile picture
		self.upload_button = MDRaisedButton(text="Upload Profile Picture", on_press=self.file_manager_open)
		self.upload_path = None

		# Back button to go back to the camera screen
		self.back_button = MDRaisedButton(text="Back", on_press=self.go_back, size_hint=(1, None), height=50)

		# Add fields to the layout
		layout.add_widget(self.name_input)
		layout.add_widget(self.email_input)
		layout.add_widget(self.mobile_input)
		layout.add_widget(self.designation_input)
		layout.add_widget(self.emp_code_input)
		layout.add_widget(self.password_input)
		layout.add_widget(self.upload_button)

		# Button to submit the registration
		self.submit_button = MDRaisedButton(text="Submit", size_hint=(1, None), height=50, on_press=self.submit_registration)
		layout.add_widget(self.submit_button)
		layout.add_widget(self.back_button)

		self.add_widget(layout)

		# File manager to handle file uploads
		self.file_manager = MDFileManager(
			exit_manager=self.exit_manager,
			select_path=self.select_path
		)

	def file_manager_open(self, instance):
		self.file_manager.show('/')  # Open file manager starting from root

	def select_path(self, path):
		self.upload_path = path
		self.exit_manager()

	def exit_manager(self, *args):
		self.file_manager.close()

	def submit_registration(self, instance):
		name = self.name_input.text
		email = self.email_input.text
		mobile = self.mobile_input.text
		designation = self.designation_input.text
		emp_code = self.emp_code_input.text
		password = self.password_input.text
		picture_path = self.upload_path

		# Hash the password for secure storage
		hashed_password = hashlib.sha256(password.encode()).hexdigest()

		# Save the profile picture to the 'uploads' directory
		if picture_path:
			try:
				print(f"Selected file path: {picture_path}")
				if not os.path.exists(UPLOAD_DIR):
					os.makedirs(UPLOAD_DIR)
				picture_filename = os.path.basename(picture_path)
				destination_path = os.path.join(UPLOAD_DIR, picture_filename)
				print(f"Copying file to: {destination_path}")
				shutil.copy(picture_path, destination_path)
			except FileNotFoundError as e:
				print(f"FileNotFoundError: {e}")
				toast("Error: File not found.")
				return
			except Exception as e:
				print(f"Error: {e}")
				toast("An error occurred while saving the profile picture.")
				return
		else:
			destination_path = None

		try:
			conn = psycopg2.connect(
				dbname=DB_NAME,
				user=DB_USER,
				password=DB_PASSWORD,
				host=DB_HOST,
				port=DB_PORT
			)
			cursor = conn.cursor()

			# Create the users table if it doesn't exist
			cursor.execute(""" 
				CREATE TABLE IF NOT EXISTS users (
					id SERIAL PRIMARY KEY,
					name VARCHAR(255),
					email VARCHAR(255) UNIQUE,
					mobile VARCHAR(20),
					designation VARCHAR(100),
					emp_code VARCHAR(100),
					password VARCHAR(255),
					profile_picture TEXT
				)
			""")

			# Insert the registration data
			cursor.execute("""
				INSERT INTO users (name, email, mobile, designation, emp_code, password, profile_picture)
				VALUES (%s, %s, %s, %s, %s, %s, %s)
			""", (name, email, mobile, designation, emp_code, hashed_password, destination_path))

			conn.commit()
			cursor.close()
			conn.close()

			toast("Registration successful!")
			self.manager.current = 'camera'

		except Exception as e:
			print(f"Database Error: {e}")
			toast("An error occurred during registration.")

	def go_back(self, instance):
		self.manager.current = 'camera'

from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.filemanager import MDFileManager
import psycopg2

class ProfileWindow(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Profile image widget at the top
        self.profile_image = Image(source="", size_hint=(1, 0.4))  # Adjust size_hint for proper size
        self.layout.add_widget(self.profile_image)

        # Profile form fields (same as the registration form)
        self.name_input = MDTextField(hint_text="Name", size_hint=(1, None), height=50)
        self.email_input = MDTextField(hint_text="Email", size_hint=(1, None), height=50)
        self.mobile_input = MDTextField(hint_text="Mobile Number", size_hint=(1, None), height=50)
        self.designation_input = MDTextField(hint_text="Designation", size_hint=(1, None), height=50)
        self.emp_code_input = MDTextField(hint_text="Employee Code", size_hint=(1, None), height=50)
        self.password_input = MDTextField(hint_text="Password", password=True, size_hint=(1, None), height=50)

        # Back button to go back to the camera screen
        self.back_button = MDRaisedButton(text="Back", on_press=self.go_back, size_hint=(1, None), height=50)

        # Add form fields and back button to the layout
        self.layout.add_widget(self.name_input)
        self.layout.add_widget(self.email_input)
        self.layout.add_widget(self.mobile_input)
        self.layout.add_widget(self.designation_input)
        self.layout.add_widget(self.emp_code_input)
        self.layout.add_widget(self.password_input)

        self.upload_path = None

        # Back button at the bottom
        self.layout.add_widget(self.back_button)

        self.add_widget(self.layout)

        # File manager to handle profile picture uploads
        self.file_manager = MDFileManager(
            exit_manager=self.exit_manager,
            select_path=self.select_path
        )

    def go_back(self, instance):
        # Return to the 'camera' screen or a previous screen
        self.manager.current = 'camera'

    def load_profile(self, email):
        try:
            conn = psycopg2.connect(
                dbname=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT
            )
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user:
                user_id, name, email, mobile, designation, emp_code, password, profile_picture = user

                # Set form fields with the user data
                self.name_input.text = name
                self.email_input.text = email
                self.mobile_input.text = mobile
                self.designation_input.text = designation
                self.emp_code_input.text = emp_code
                self.password_input.text = password  # You may not want to display the password directly

                # Handle profile picture
                if profile_picture:
                    self.profile_image.source = profile_picture  # Set image source to the profile picture path
                    self.upload_path = profile_picture
                else:
                    print("No profile picture available.")
                    self.profile_image.source = ""  # Reset the image source if no picture

            else:
                print("No profile found for the given email.")

            cursor.close()
            conn.close()

        except Exception as e:
            print(f"Database Error: {e}")

    def file_manager_open(self, *args):
        # Open file manager to upload profile picture
        self.file_manager.show('/path/to/your/directory')  # Set initial directory here

    def exit_manager(self, *args):
        self.file_manager.close()

    def select_path(self, path):
        # Called when a profile picture is selected
        self.upload_path = path
        self.profile_image.source = path  # Display the selected image
        print(f"Selected profile picture path: {path}")
        self.file_manager.close()









class MyApp(MDApp):
	def build(self):
		sm = ScreenManager()
		sm.add_widget(CameraWindow(name='camera'))
		sm.add_widget(RegistrationWindow(name='register'))
		sm.add_widget(ProfileWindow(name='profile'))
		return sm

if __name__ == '__main__':
	MyApp().run()
