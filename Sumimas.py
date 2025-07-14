
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import configparser
import os
import time
import uuid
import sqlite3
import openpyxl
from pathlib import Path
from tkinter import filedialog
import customtkinter
from PIL import Image, ImageTk, ImageDraw, ImageFont
from io import BytesIO
from cryptography.fernet import Fernet
import numpy as np

# Configuración de cifrado (mantener igual que el original)
clave_cifrado = b'jvXOzwTyfQusXwZBgh0d2GdT0gMCvdR8oOWkFQPpx9o='
fernet = Fernet(clave_cifrado)


class SerialInterface:
    def __init__(self, root):
        self.root = root        
        self.root.title("MONTRA")

        # Inicializar la variable de motivos con un valor vacío
        self.motivos_var = tk.StringVar(value="")

        
        # Colores y estilos para la nueva interfaz
        self.colorbackground = "#36474f"
        self.color_botones = "#4a636f"
        self.color_botones_hover = "#5b7684"
        self.color_texto_botones = "white"
        
        # Crear frame principal
        self.main_frame = tk.Frame(root, bg=self.colorbackground)
        self.main_frame.pack(fill="both", expand=True)
        
        # Crear el panel lateral (sidebar)
        self.sidebar = tk.Frame(self.main_frame, bg=self.colorbackground, width=200)
        self.sidebar.pack(side="left", fill="y")
        
        # Crear el contenedor de contenido (contendrá los frames de medición y configuración)
        self.content_container = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.content_container.pack(side="right", fill="both", expand=True)
        
        # Crear los frames de medición y configuración (inicialmente ocultos)
        self.medicion_frame = tk.Frame(self.content_container, bg="#f0f0f0")
        self.configuracion_frame = tk.Frame(self.content_container, bg="#f0f0f0")
        # Cargar imágenes
        self.imagenes()
        
        # Crear la barra lateral con los botones
        self.create_sidebar()
        
        # Crear contenido de las secciones
        self.create_configuracion_tab()
        self.cargar_configuracion()
        self.create_medicion_tab()
        
        # Mostrar inicialmente la sección de medición
        self.show_medicion()

        
        # Configuración después de cargar la ventana
        self.root.after(100, self.cargar_icono)

        # Para el cierre controlado de la aplicación
        self.root.protocol("WM_DELETE_WINDOW", self.cerrar_aplicacion)

        
    def create_sidebar(self):
        """Crea la barra lateral con los botones de navegación"""
        # Frame para el logo
        logo_frame = tk.Frame(self.sidebar, bg=self.colorbackground, height=150)
        logo_frame.pack(fill="x", padx=10, pady=(30, 20))
        
        # Logo MONTRA
        label_montra = ttk.Label(logo_frame, image=self.logo_montra, background=self.colorbackground)
        label_montra.pack(pady=10)
        
        # Separador
        separator = ttk.Separator(self.sidebar, orient="horizontal")
        separator.pack(fill="x", padx=10, pady=10)
        
        # Estilo para los botones
        button_style = {
            "width": 180,
            "height": 45,
            "corner_radius": 8,
            "fg_color": self.color_botones,
            "hover_color": self.color_botones_hover,
            "text_color": self.color_texto_botones,
            "font": ("Helvetica", 14, "bold")
        }
        
        # Botón de Medición
        self.medicion_button = customtkinter.CTkButton(
            self.sidebar, 
            text="MEDICIÓN",
            command=self.show_medicion,
            **button_style
        )
        self.medicion_button.pack(padx=10, pady=10)
        
        # Botón de Configuración
        self.configuracion_button = customtkinter.CTkButton(
            self.sidebar, 
            text="CONFIGURACIÓN",
            command=self.show_configuracion,
            **button_style
        )
        self.configuracion_button.pack(padx=10, pady=10)

    def show_medicion(self):
        """Muestra el panel de medición y oculta el de configuración"""
        self.configuracion_frame.pack_forget()
        self.medicion_frame.pack(fill="both", expand=True, padx=10)
        # Resaltar el botón activo
        self.medicion_button.configure(fg_color="#1f5c87")  # Color más oscuro para indicar activo
        self.configuracion_button.configure(fg_color=self.color_botones)  # Color normal
        # Dar foco al campo remision
        if hasattr(self, 'pieza_entry'):
            self.pieza_entry.focus_set()

    def show_configuracion(self):
        """Muestra el panel de configuración después de verificar credenciales"""
        # Verificar credenciales antes de mostrar la configuración
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Acceso")
        
        # Posicionar la ventana en el centro de la aplicación principal
        # Aumentado el alto para asegurar que el botón se vea completo
        position_x = int(self.root.winfo_x() + (self.root.winfo_width() / 2) - (350 / 2))
        position_y = int(self.root.winfo_y() + (self.root.winfo_height() / 2) - (220 / 2))
        self.login_window.geometry(f"{350}x{250}+{position_x}+{position_y}")
        self.login_window.resizable(False, False)
        self.login_window.attributes("-topmost", True)
        
        # Configurar colores y estilos consistentes
        self.login_window.configure(bg="#f0f0f0")
        
        # Crear un frame contenedor para todos los elementos
        login_frame = tk.Frame(self.login_window, bg="#f0f0f0", padx=25, pady=25)
        login_frame.pack(fill="both", expand=True)
        
        # Asegurar que las columnas se expandan correctamente
        login_frame.columnconfigure(1, weight=1)  # La segunda columna (con los campos) debe expandirse
        
        # Título de la ventana
        title_label = tk.Label(
            login_frame, 
            text="Ingrese sus Credenciales", 
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Campo de usuario
        username_label = tk.Label(
            login_frame, 
            text="Usuario:", 
            font=("Helvetica", 11),
            bg="#f0f0f0",
            anchor="w",
            width=10  # Ancho fijo para la etiqueta
        )
        username_label.grid(row=1, column=0, padx=5, pady=8, sticky="w")
        
        # Entry para usuario con tamaño fijo
        username_var = tk.StringVar()
        username_entry = ttk.Entry(
            login_frame, 
            textvariable=username_var,
            font=("Helvetica", 11),
            width=20  # Ancho explícito en caracteres
        )
        username_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        username_entry.focus_set()
        
        # Campo de contraseña
        password_label = tk.Label(
            login_frame, 
            text="Contraseña:", 
            font=("Helvetica", 11),
            bg="#f0f0f0",
            anchor="w",
            width=10  # Ancho fijo para la etiqueta
        )
        password_label.grid(row=2, column=0, padx=5, pady=8, sticky="w")
        
        # Entry para contraseña con tamaño fijo
        password_var = tk.StringVar()
        password_entry = ttk.Entry(
            login_frame, 
            textvariable=password_var,
            show="*", 
            font=("Helvetica", 11),
            width=20  # Ancho explícito en caracteres
        )
        password_entry.grid(row=2, column=1, padx=5, pady=8, sticky="ew")

        # Espacio para separar los campos del botón
        spacer = tk.Frame(login_frame, height=20, bg="#f0f0f0")
        spacer.grid(row=3, column=0, columnspan=2)
        
        # Método para verificar credenciales (local al método, no atributo de clase)
        def check_credentials_local():
            username = username_var.get()
            password = password_var.get()
            if self.verify_credentials(username, password):
                # Acceso permitido a la pestaña de configuración
                self.login_window.destroy()
                self.medicion_frame.pack_forget()
                self.configuracion_frame.pack(fill="both", expand=True)
                # Resaltar el botón activo
                self.configuracion_button.configure(fg_color="#1f5c87")
                self.medicion_button.configure(fg_color=self.color_botones)
            else:
                # Usuario no autenticado o no es SUPERUSUARIO
                self.login_window.destroy()
                messagebox.showerror("Acceso denegado", "No se pudo verificar su identidad para confirmar acceso a la ventana 'Configuración'.")
        
        # Botón de ingreso con estilo consistente (usando el ancho completo disponible)
        login_button = tk.Button(
            login_frame,
            text="Ingresar",
            font=("Helvetica", 11),
            bg="#1f5c87",  # Usando el mismo azul de los otros botones
            fg="white",
            relief="flat",
            height=2,
            width=15,  # Ancho fijo en caracteres
            command=check_credentials_local
        )
        login_button.grid(row=4, column=0, columnspan=2, pady=15)
        
        # Espacio adicional en la parte inferior para evitar cortes
        bottom_spacer = tk.Frame(login_frame, height=10, bg="#f0f0f0")
        bottom_spacer.grid(row=5, column=0, columnspan=2)
        
        # Vincular la tecla Enter para activar el botón de ingreso
        self.login_window.bind("<Return>", lambda event: check_credentials_local())
        
        # Manejo adecuado de la ventana
        self.login_window.grab_set()
        self.login_window.protocol("WM_DELETE_WINDOW", self.cerrar_ventana)
        
        # Configurar icono
        try:
            self.login_window.iconbitmap('Icons/montra.ico')
        except:
            pass

    def cerrar_ventana(self):
        self.login_window.destroy()
    
    def imagenes(self):
        # Cargar y redimensionar los logos para la interfaz
        self.logo_montra = tk.PhotoImage(file="Icons/Montra_sidebar_small.png")
        #self.logo_montra = self.logo_montra.subsample(1, 1)  # Redimensionado para el sidebar
        
        self.logo_cubiscan = tk.PhotoImage(file="Icons/CUBISCAN.png")
        self.logo_cubiscan = self.logo_cubiscan.subsample(20, 20)
        
        self.logo_deprisa = tk.PhotoImage(file="Icons/Deprisa_logo.png")
        self.logo_deprisa = self.logo_deprisa.subsample(1, 1)
    
    def verify_credentials(self, username, password):
        # Verificar las credenciales en la base de datos y devolver True si son válidas, False si no
        conn = sqlite3.connect('Montradb.db')
        cursor = conn.cursor()
        cursor.execute('SELECT Acceso FROM Login WHERE Usuario = ? AND Contraseña = ?', (username, password))
        resultado = cursor.fetchone()
        conn.close()
        return resultado is not None and resultado[0] == "SUPERUSUARIO"

    def cargar_icono(self):
        try:
            self.root.iconbitmap("Icons/montra.ico")
        except:
            pass
        
    #CREACION DE METODO DE CIERRE DE APLICACIÓN
    def cerrar_aplicacion(self):
        self.guardar_configuracion()  # Guardar la configuración antes de salir
        self.root.unbind("<Configure>")  # Desvincula el evento de redimensionamiento
        self.root.destroy()  # Cerrar la aplicación

    def create_medicion_tab(self):
        self.prueba=""
        #Espacio para crear la pestaña de medición
    
    #CONFIGURACIÓN DE ARCHIVO.INI PARA PRECARGAR Y GUARDAR LOS DATOS
    def cargar_configuracion(self):
        config = configparser.ConfigParser()
        try:
            config.read('configuracion.ini')
            if 'Configuracion' in config:
                # Desencriptar y cargar los valores de configuración
                motivos_guardados = self.desencriptar(config['Configuracion'].get('motivos_var', ''))
                if motivos_guardados:
                    self.motivos_var.set(motivos_guardados)
                else:
                    pass
                # Actualizar el widget Text después de crear la interfaz
                self.root.after(500, self.actualizar_texto_motivos)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar configuración: {e}")

    def actualizar_texto_motivos(self):
        """Actualiza el widget Text de motivos con el valor de motivos_var."""
        if hasattr(self, 'motivos_text') and hasattr(self, 'motivos_var'):
            # Limpiar primero el contenido actual
            self.motivos_text.delete("1.0", tk.END)
            # Insertar el valor de motivos_var
            self.motivos_text.insert("1.0", self.motivos_var.get())

    def guardar_configuracion(self):
        config = configparser.ConfigParser()
        if not config.has_section('Configuracion'):
            config.add_section('Configuracion')
            # Guardar los motivos configurados
        # Asegurarse de que motivos_var se actualiza con el contenido actual del Text widget
        if hasattr(self, 'motivos_text'):
            motivos_texto = self.motivos_text.get("1.0", "end-1c")
            self.motivos_var.set(motivos_texto)
        
        # Guardar el valor actualizado
        if hasattr(self, 'motivos_var'):
            config['Configuracion']['motivos_var'] = self.encriptar(self.motivos_var.get())
        # Obtener el último puerto seleccionado del combobox
        if hasattr(self, 'puertos_combobox'):
            ultimo_puerto = self.puertos_combobox.get()
            config['Configuracion']['ultimo_puerto'] = self.encriptar(ultimo_puerto)
        
        with open('configuracion.ini', 'w') as configfile:
            config.write(configfile)
    
    def encriptar(self, valor):
        # Cifra el valor utilizando la clave de cifrado
        if not valor:
            valor = ""
        return fernet.encrypt(valor.encode()).decode()

    def desencriptar(self, valor_cifrado):
        # Descifra el valor utilizando la clave de cifrado
        if not valor_cifrado:
            return ""
        token = valor_cifrado.encode()
        return fernet.decrypt(token).decode()
    
    # 2. Ahora modificamos create_configuracion_tab para añadir el campo de motivos en la sección "DATOS CLIENTE"
    def create_configuracion_tab(self):

        self.motivos_var = tk.StringVar()
        
        
        # Configuración del frame principal - mismo fondo que la ventana de medición
        self.configuracion_frame.configure(bg="#f0f0f0")
        self.configuracion_frame.columnconfigure(0, weight=1)
        self.configuracion_frame.rowconfigure(0, weight=1)
        
        # Crear el contenedor principal con el mismo color de fondo
        config_container = tk.Frame(self.configuracion_frame, bg="#f0f0f0", padx=20, pady=20)
        config_container.grid(row=0, column=0, sticky="nsew")
        
        # --- Sección Web Service ---
        # Usando el mismo estilo que los frame de la ventana de medición
        ws_frame = tk.LabelFrame(
            config_container, 
            text="DATOS CLIENTE", 
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 11, 'bold')
        )
        ws_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)

        # Añadir nuevo campo para motivos (multiline)
        tk.Label(ws_frame, text="Motivos:", bg="#f0f0f0", font=('Helvetica', 11)).grid(
            row=0, column=2, padx=10, pady=5, sticky="nw"
        )
        
        # Crear un Text widget para motivos
        self.motivos_text = tk.Text(ws_frame, width=30, height=5, font=('Helvetica', 11))
        self.motivos_text.grid(row=0, column=3, rowspan= 3, padx=10, pady=5, sticky="w")
        
        # Insertar el valor actual de motivos_var si existe
        if hasattr(self, 'motivos_var') and self.motivos_var.get():
            self.motivos_text.delete("1.0", tk.END)  # Limpiar primero
            self.motivos_text.insert("1.0", self.motivos_var.get())
        
        
        # Función para actualizar motivos_var cuando cambie el texto
        def update_motivos_var(event=None):
            self.motivos_var.set(self.motivos_text.get("1.0", "end-1c"))
        
        # Vincular a eventos de cambio en el texto
        self.motivos_text.bind("<KeyRelease>", update_motivos_var)
        
if __name__ == "__main__":
    # Configurar tema de customtkinter
    customtkinter.set_appearance_mode("Dark")  # Modos: "System" (por defecto), "Dark", "Light"
    customtkinter.set_default_color_theme("blue")  # Temas: "blue" (por defecto), "green", "dark-blue"
    
    # Iniciar aplicación
    root = tk.Tk()
    root.state('zoomed')
    root.title("MONTRA - Sistema de Medición")
    
    # Establecer un tamaño mínimo para la ventana
    root.minsize(1024, 768)
    
    # Crear la aplicación
    app = SerialInterface(root)
    
    # Iniciar el loop principal
    root.mainloop()