# Importing necessary libraries and modules
import tkinter as tk
from tkinter import ttk, Label, Toplevel, messagebox
from PIL import Image, ImageTk
import serial
import threading
import webbrowser
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy.stats import linregress
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import time
import csv
import re
import os

# Defining a window for copyright notice
class CopyrightWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Copyright Notice")
        self.geometry("300x150")
        label = tk.Label(self, text="© 2023 SolarStage Pty Ltd.\nAll rights reserved.")
        label.pack(pady=40, padx=40)


# Main controller for the STM32 microcontroller
class STM32Controller(tk.Tk):
    def __init__(self, port, baudrate=115200):
        super().__init__()
        self.prev_valid_temp = None
        self.ser = serial.Serial(port, baudrate, timeout=1) # Initialize serial communication
        self.ser.flush()
        self.title("STM32 Controller")
        self.ser.flush()
        self.title("STM32 Controller")
        self.interrupted = False  # Flag for interruption
        self.temperatures = []  # List to store temperature data
        self.configure(bg='#FFFFFF')  # Set background color for main window
        self.create_widgets()

        # Start a background thread to read temperatures periodically
        self.temp_thread = threading.Thread(target=self.read_temperature, daemon=True)
        self.temp_thread.start()

    def create_widgets(self):
        # Create a ttk style object
        style = ttk.Style()
        style.configure('TButton', font=("Arial", 16), background='#E0E0E0')  # 扁平化设计和柔和的背景颜色
        style.configure('TLabel', font=("Arial", 16), background='#FFFFFF')  # 设置背景颜色为白色

        # Creating main frame
        main_frame = tk.Frame(self, bg='#FFFFFF')
        main_frame.pack(pady=20, padx=20, fill='both', expand=True)

        # Load and display the ANU logo at top-left corner
        self.anu_image = Image.open("anu_logo.png")
        self.anu_photo = ImageTk.PhotoImage(self.anu_image)
        self.anu_logo_label = Label(main_frame, image=self.anu_photo, bg='#FFFFFF')
        self.anu_logo_label.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

        # Main title in the center-top of the main frame
        self.title_label = ttk.Label(main_frame, text="SolarStage System", font=("Arial", 24))
        self.title_label.grid(row=0, column=1, pady=20, padx=(80, 40), sticky='nsew')

        # Frame for operation buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10, fill='x', expand=True)

        btn_font = ("Arial", 12)
        btn_width = 20
        btn_height = 2

        # Display the copyright notice at the bottom
        self.copyright_label = tk.Label(self, text="© 2023 SolarStage Team")
        self.copyright_label.pack(side='bottom', pady=10)

        # Creating buttons for User Manual, Start Testing and Quit
        self.repo_btn = tk.Button(btn_frame, text="User\nManual", command=self.user_manual, font=btn_font, width=btn_width, height=btn_height, bg='#E0E0E0', bd=0)
        self.repo_btn.pack(side='left', padx=55)

        self.start_test_btn = tk.Button(btn_frame, text="Start\nTesting", command=self.open_test_window, font=btn_font, width=btn_width, height=btn_height, bg='#E0E0E0', bd=0)
        self.start_test_btn.pack(side='left', padx=55)

        self.quit_btn = tk.Button(btn_frame, text="Quit", command=self.quit_app, font=btn_font, width=btn_width, height=btn_height, bg='#E0E0E0', bd=0)
        self.quit_btn.pack(side='left', padx=55)

        # Create the graph to plot temperature data
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(pady=10, padx=10, expand=True, fill='both')

        # Initialize the graph settings
        self.ax.set_title("Temperature Over Time")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Temperature (°C)")
        self.ax.set_xlim(0, 5, 15)
        self.ax.set_ylim(0, 50)
        self.line, = self.ax.plot([], [], '-o', label="Temperature (°C)")
        self.ax.legend()
        self.fig.tight_layout()
        self.fig.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1) 

        # Load and display the stage image
        self.stage_image = Image.open("1.png")
        self.stage_photo = ImageTk.PhotoImage(self.stage_image)
        self.stage_label = Label(self, image=self.stage_photo, bg='#FFFFFF')
        self.stage_label.pack(padx=3, pady=3, fill='both', expand=True)

       # Label to display the URL link
        self.url_label = Label(self, text="Visit our website", fg="blue", cursor="hand2")
        self.url_label.pack(side="bottom", pady=10)
        self.url_label.bind("<Button-1>", self.open_website) 

    # Creates a separate window to show copyright info
    def show_copyright(self):
        CopyrightWindow(self)

    # Opens a window with controls to set and test temperature
    def open_test_window(self):
        test_window = Toplevel(self)
        test_window.title("Test Controls")

        ttk.Label(test_window, text="Set Temperature (-190-230°C):").pack(padx=20, pady=5)
        self.temp_var = tk.StringVar()
        ttk.Entry(test_window, textvariable=self.temp_var).pack(padx=20, pady=5)
        ttk.Button(test_window, text="Set Temperature", command=self.send_temperature).pack(padx=20, pady=5)
        ttk.Button(test_window, text="Interrupt", command=self.set_interrupt).pack(padx=20, pady=5)

    # Sends a given command to the serial device and prints the response
    def send_cmd(self, cmd):
        self.ser.write(cmd)
        line = self.ser.readline().decode('utf-8').rstrip()
        print("Sent", line)

    # Sets the interrupt flag and notifies the user
    def set_interrupt(self):
        self.interrupted = True
        print("Operation interrupted")

    # Opens a predefined website in the default web browser
    def open_website(self, event):
        import webbrowser
        webbrowser.open("https://u7443981.wixsite.com/solarstage")

    #Sends the desired temperature setting to the device if it's within range
    def send_temperature(self):
        if not self.interrupted:
            try:
                temp = int(self.temp_var.get())
                if -190 <= temp <= 230:
                # Choose a different command prefix for positive and negative numbers
                    prefix = b'010' if temp >= 0 else b'011'
                # Convert the temperature value to absolute and format it for sending
                    temp_str_abs = str(abs(temp)).zfill(3)
                    cmd = prefix + temp_str_abs.encode() + b'\r\n'
                    self.ser.write(cmd)
                # Display a window showing the set temperature
                    self.popup_temperature(str(temp))
                    line = self.ser.readline().decode('utf-8').rstrip()
                    if not line.startswith("Temp:"):
                        print("Unexpected response:", line)
                else:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Error", "Invalid temperature! Please enter a value between -190 and 230.")
                self.set_interrupt()

    def popup_temperature(self, temperature):
    # Opens a new window to display the temperature that's been set
        temp_window = tk.Toplevel(self)
        temp_window.title("Temperature Set")
        label = tk.Label(temp_window, text=f"Set Temperature: {temperature}°C", font=("Arial", 14))
        label.pack(pady=20, padx=20)
        close_btn = tk.Button(temp_window, text="Close", command=temp_window.destroy)
        close_btn.pack(pady=10)

    # Continuously requests and reads temperature data from the device
    def read_temperature(self):
        start_time = time.time()
        self.temperatures = []
        self.times = []
        data_received = True  # Indicator to control data request flow
        while True:
            if not self.interrupted:
            # If data is received, send a request immediately
                if data_received:
                    self.ser.write(b'11\r\n')
                    data_received = False  # After sending, wait for a response
                
                raw_data = self.ser.readline()
                if not raw_data:  # If no data was received, loop back to the beginning
                    time.sleep(1)  # Wait for 1 second if no reply is received
                    continue

                data_received = True  # Data received, so a new request can be sent immediately

                try:
                    line = raw_data.decode('utf-8').rstrip()
                    print("Temperature:" , line)
                    print("   Length :", len(line), "characters")
                    print("   Type   :", type(line))
                    print("   Bytes  :", raw_data)
                # Add temperature and time to the lists
                    temp = float(line) 
                    elapsed_time = time.time() - start_time
                    self.temperatures.append(temp)
                    self.times.append(elapsed_time)

                # Update the plot
                    self.update_plot()

                except UnicodeDecodeError:
                    print("Received non-UTF-8 data:", raw_data)
                time.sleep(8)  
    
    # Updates the temperature vs. time plot with new data
    def update_plot(self):
        self.ax.clear()
        if self.times:
            self.ax.plot(self.times, self.temperatures, '-o', label="Temperature (°C)")
            max_time = self.times[-1]
            self.ax.set_xlim(0, max_time + 1)
        
            current_temp_str = f"{self.temperatures[-1]}°C"
            self.ax.text(0.05, 0.95, f"Current Temperature: {current_temp_str}",
                     transform=self.ax.transAxes, verticalalignment='top', backgroundcolor='white')
            self.canvas.draw()
        else:
            print("No data to plot.")

    # 动态地设置x轴的限制
        #max_time = self.times[-1] if self.times else 0 
        #self.ax.set_xlim(0, max_time + 1)  
        #self.ax.legend()
        #self.canvas.draw()

    # Closes the application, saves data to Excel, and releases resources
    def quit_app(self):
        # Convert the temperatures and times to a DataFrame
        self.temperature_data = pd.DataFrame({
            'Time': self.times,
            'Temperature': self.temperatures
        })

        # Save the DataFrame to Excel
        self.temperature_data.to_excel("temperature_data.xlsx", index=False, engine='openpyxl')
        print("Data saved to:", os.path.join(os.getcwd(), "temperature_data.xlsx"))

        if self.ser.is_open:
            self.ser.close()

        self.quit()  
    
    # Opens the user manual in the default PDF viewer
    def user_manual(self):
        webbrowser.open(r"D:\ANU\User_Manual.pdf")
    
    # Continuously reads data from the serial port and displays it
    def read_serial(self):
        while not self.interrupted:
            if self.ser.in_waiting:
                raw_data = self.ser.readline()
                try:
                    line = raw_data.decode('utf-8').rstrip()
                    print("Received from Serial:")
                    print("   Data   :", line)
                    print("   Length :", len(line), "characters")
                    print("   Type   :", type(line))
                    print("   Bytes  :", raw_data)
                except UnicodeDecodeError:
                    print("Received non-UTF-8 data:", raw_data)
            time.sleep(2) 


if __name__ == "__main__":
    app = STM32Controller(port="COM3", baudrate=115200)
    app.mainloop()