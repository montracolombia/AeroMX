import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import *
import configparser
import os
import time
import uuid
import sqlite3
from pathlib import Path
from tkinter import filedialog
import customtkinter
from PIL import Image, ImageTk, ImageDraw, ImageFont
from io import BytesIO
from cryptography.fernet import Fernet
import numpy as np
import qrcode
from datetime import datetime
import hashlib
import base64

# Configuración de cifrado para archivos de configuración
clave_cifrado = b'jvXOzwTyfQusXwZBgh0d2GdT0gMCvdR8oOWkFQPpx9o='
fernet = Fernet(clave_cifrado)

# Clase para manejar la base de datos encriptada
class MontraDB:
    def __init__(self, archivo_encriptado="Montradb.db", password="MiPasswordSeguro123"):
        self.archivo_encriptado = archivo_encriptado
        self.conn = None
        
        # Generar clave desde password
        key = hashlib.sha256(password.encode()).digest()
        self.key = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(self.key)
    
    def conectar(self):
        """Conecta a la base encriptada directamente en memoria"""
        try:
            if not os.path.exists(self.archivo_encriptado):
                return False
            
            # Leer archivo encriptado
            with open(self.archivo_encriptado, 'rb') as f:
                datos_encriptados = f.read()
            
            # Desencriptar
            datos_db = self.cipher.decrypt(datos_encriptados)
            
            # Crear conexión en memoria
            self.conn = sqlite3.connect(":memory:")
            
            # Restaurar base de datos directamente en memoria
            self.conn.deserialize(datos_db)
            
            return True
            
        except Exception as e:
            print(f"Error al conectar: {e}")
            return False
    
    def desconectar(self):
        """Cierra conexión y limpia memoria"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def verificar_credenciales(self, username, password):
        """Verifica credenciales en la base encriptada"""
        if not self.conn:
            return False
        
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT Acceso FROM Login WHERE Usuario = ? AND Contraseña = ?', (username, password))
            resultado = cursor.fetchone()
            return resultado is not None and resultado[0] == "SUPERUSUARIO"
        except Exception as e:
            print(f"Error al verificar credenciales: {e}")
            return False

class SerialInterface:
    def __init__(self, root):
        self.root = root        
        self.root.title("MONTRA")

        # Inicializar la base de datos encriptada
        self.db = MontraDB()
        if not self.db.conectar():
            messagebox.showerror("Error", "No se pudo conectar a la base de datos encriptada")
            return

        # Inicializar variables
        self.motivos_var = tk.StringVar(value="")
        self.destino_var = tk.StringVar(value="")
        self.clave_cliente_var = tk.StringVar(value="")
        
        # Variables para QR
        self.qr_codes = []
        self.qr_actual = 0
        
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
        
        # Crear el contenedor de contenido
        self.content_container = tk.Frame(self.main_frame, bg="#f0f0f0")
        self.content_container.pack(side="right", fill="both", expand=True)
        
        # Crear los frames
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
        try:
            label_montra = ttk.Label(logo_frame, image=self.logo_montra, background=self.colorbackground)
            label_montra.pack(pady=10)
        except:
            # Si no hay logo, usar texto
            label_montra = tk.Label(logo_frame, text="MONTRA", font=("Helvetica", 20, "bold"), 
                                   bg=self.colorbackground, fg="white")
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
        """Muestra el panel de medición"""
        self.configuracion_frame.pack_forget()
        self.medicion_frame.pack(fill="both", expand=True, padx=10)
        self.medicion_button.configure(fg_color="#1f5c87")
        self.configuracion_button.configure(fg_color=self.color_botones)

    def show_configuracion(self):
        """Muestra el panel de configuración después de verificar credenciales"""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Acceso")
        
        position_x = int(self.root.winfo_x() + (self.root.winfo_width() / 2) - (350 / 2))
        position_y = int(self.root.winfo_y() + (self.root.winfo_height() / 2) - (220 / 2))
        self.login_window.geometry(f"{350}x{250}+{position_x}+{position_y}")
        self.login_window.resizable(False, False)
        self.login_window.attributes("-topmost", True)
        self.login_window.configure(bg="#f0f0f0")
        
        login_frame = tk.Frame(self.login_window, bg="#f0f0f0", padx=25, pady=25)
        login_frame.pack(fill="both", expand=True)
        login_frame.columnconfigure(1, weight=1)
        
        # Título
        title_label = tk.Label(
            login_frame, 
            text="Ingrese sus Credenciales", 
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="ew")
        
        # Usuario
        username_label = tk.Label(
            login_frame, 
            text="Usuario:", 
            font=("Helvetica", 11),
            bg="#f0f0f0",
            anchor="w",
            width=10
        )
        username_label.grid(row=1, column=0, padx=5, pady=8, sticky="w")
        
        username_var = tk.StringVar()
        username_entry = ttk.Entry(
            login_frame, 
            textvariable=username_var,
            font=("Helvetica", 11),
            width=20
        )
        username_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        username_entry.focus_set()
        
        # Contraseña
        password_label = tk.Label(
            login_frame, 
            text="Contraseña:", 
            font=("Helvetica", 11),
            bg="#f0f0f0",
            anchor="w",
            width=10
        )
        password_label.grid(row=2, column=0, padx=5, pady=8, sticky="w")
        
        password_var = tk.StringVar()
        password_entry = ttk.Entry(
            login_frame, 
            textvariable=password_var,
            show="*", 
            font=("Helvetica", 11),
            width=20
        )
        password_entry.grid(row=2, column=1, padx=5, pady=8, sticky="ew")

        spacer = tk.Frame(login_frame, height=20, bg="#f0f0f0")
        spacer.grid(row=3, column=0, columnspan=2)
        
        def check_credentials_local():
            username = username_var.get()
            password = password_var.get()
            if self.db.verificar_credenciales(username, password):
                self.login_window.destroy()
                self.medicion_frame.pack_forget()
                self.configuracion_frame.pack(fill="both", expand=True)
                self.configuracion_button.configure(fg_color="#1f5c87")
                self.medicion_button.configure(fg_color=self.color_botones)
            else:
                self.login_window.destroy()
                messagebox.showerror("Acceso denegado", "Credenciales incorrectas")
        
        login_button = tk.Button(
            login_frame,
            text="Ingresar",
            font=("Helvetica", 11),
            bg="#1f5c87",
            fg="white",
            relief="flat",
            height=2,
            width=15,
            command=check_credentials_local
        )
        login_button.grid(row=4, column=0, columnspan=2, pady=15)
        
        self.login_window.bind("<Return>", lambda event: check_credentials_local())
        self.login_window.grab_set()
        self.login_window.protocol("WM_DELETE_WINDOW", lambda: self.login_window.destroy())

    def imagenes(self):
        """Cargar imágenes o usar texto como fallback"""
        try:
            self.logo_montra = tk.PhotoImage(file="Icons/Montra_sidebar_small.png")
        except:
            self.logo_montra = None
        
        try:
            self.logo_cubiscan = tk.PhotoImage(file="Icons/CUBISCAN.png")
            self.logo_cubiscan = self.logo_cubiscan.subsample(20, 20)
        except:
            self.logo_cubiscan = None
        
        try:
            self.logo_deprisa = tk.PhotoImage(file="Icons/Deprisa_logo.png")
        except:
            self.logo_deprisa = None
    
    def cargar_icono(self):
        """Cargar icono de la aplicación"""
        try:
            self.root.iconbitmap("Icons/montra.ico")
        except:
            pass
        
    def cerrar_aplicacion(self):
        """Cierra la aplicación guardando configuración"""
        self.guardar_configuracion()
        self.db.desconectar()
        self.root.destroy()

    def create_medicion_tab(self):
        """Crea la interfaz de medición con QR"""
        # Configuración del frame principal
        self.medicion_frame.configure(bg="#f0f0f0")
        self.medicion_frame.columnconfigure(0, weight=1)
        self.medicion_frame.rowconfigure(0, weight=1)
        
        # Contenedor principal
        main_container = tk.Frame(self.medicion_frame, bg="#f0f0f0", padx=20, pady=20)
        main_container.grid(row=0, column=0, sticky="nsew")
        main_container.columnconfigure(0, weight=1)
        
        # Frame de configuración
        config_frame = tk.LabelFrame(
            main_container,
            text="CONFIGURACIÓN DE CÓDIGOS QR",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold')
        )
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # Destino
        tk.Label(config_frame, text="Destino:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        
        self.destino_combo = ttk.Combobox(config_frame, width=25, font=('Helvetica', 11))
        self.destino_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Cliente
        tk.Label(config_frame, text="Cliente:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=2, padx=10, pady=10, sticky="w"
        )
        
        self.cliente_combo = ttk.Combobox(config_frame, width=25, font=('Helvetica', 11))
        self.cliente_combo.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        # Cantidad de Pallets
        tk.Label(config_frame, text="Cantidad de Pallets:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=1, column=0, padx=10, pady=10, sticky="w"
        )
        
        # Validación para solo números
        def validar_numero(char):
            return char.isdigit()
        
        vcmd = (self.root.register(validar_numero), '%S')
        
        self.cantidad_entry = tk.Entry(config_frame, width=15, font=('Helvetica', 11), validate='key', validatecommand=vcmd)
        self.cantidad_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        # Botón Generar
        self.generar_button = customtkinter.CTkButton(
            config_frame,
            text="Generar Códigos",
            command=self.generar_qr_codes,
            width=150,
            height=40,
            font=("Helvetica", 12, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        self.generar_button.grid(row=1, column=2, columnspan=2, padx=10, pady=10)
        
        # Frame para mostrar QR
        self.qr_frame = tk.LabelFrame(
            main_container,
            text="CÓDIGOS QR GENERADOS",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold')
        )
        self.qr_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.qr_frame.columnconfigure(0, weight=1)
        self.qr_frame.rowconfigure(0, weight=1)
        
        # Contenedor para QR
        qr_container = tk.Frame(self.qr_frame, bg="#f0f0f0")
        qr_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        qr_container.columnconfigure(0, weight=1)
        
        # Label para mostrar QR
        self.qr_label = tk.Label(qr_container, bg="#f0f0f0", text="Genere códigos QR para visualizar")
        self.qr_label.grid(row=0, column=0, pady=20)
        
        # Frame de navegación
        nav_frame = tk.Frame(qr_container, bg="#f0f0f0")
        nav_frame.grid(row=1, column=0, pady=10)
        
        # Botones de navegación
        self.prev_button = customtkinter.CTkButton(
            nav_frame,
            text="◀ Anterior",
            command=self.qr_anterior,
            width=100,
            height=30,
            font=("Helvetica", 10),
            fg_color="#4a636f",
            hover_color="#5b7684"
        )
        self.prev_button.pack(side="left", padx=5)
        
        self.qr_info_label = tk.Label(nav_frame, text="", bg="#f0f0f0", font=('Helvetica', 11, 'bold'))
        self.qr_info_label.pack(side="left", padx=20)
        
        self.next_button = customtkinter.CTkButton(
            nav_frame,
            text="Siguiente ▶",
            command=self.qr_siguiente,
            width=100,
            height=30,
            font=("Helvetica", 10),
            fg_color="#4a636f",
            hover_color="#5b7684"
        )
        self.next_button.pack(side="left", padx=5)
        
        # Inicialmente ocultar navegación
        self.prev_button.configure(state="disabled")
        self.next_button.configure(state="disabled")
        
        # Permitir que el frame QR se expanda
        main_container.rowconfigure(1, weight=1)
        
        # Actualizar comboboxes
        self.actualizar_comboboxes()
    
    def actualizar_comboboxes(self):
        """Actualiza los comboboxes con los valores de configuración"""
        # Destino
        destinos = self.destino_var.get().split('\n') if self.destino_var.get() else []
        destinos = [d.strip() for d in destinos if d.strip()]
        self.destino_combo['values'] = destinos
        
        # Cliente
        clientes = self.clave_cliente_var.get().split('\n') if self.clave_cliente_var.get() else []
        clientes = [c.strip() for c in clientes if c.strip()]
        self.cliente_combo['values'] = clientes
    
    def generar_qr_codes(self):
        """Genera los códigos QR según la configuración"""
        try:
            # Validar datos
            destino = self.destino_combo.get().strip()
            cliente = self.cliente_combo.get().strip()
            cantidad = self.cantidad_entry.get().strip()
            
            if not destino:
                messagebox.showerror("Error", "Seleccione un destino")
                return
            
            if not cliente:
                messagebox.showerror("Error", "Seleccione un cliente")
                return
            
            if not cantidad or int(cantidad) <= 0:
                messagebox.showerror("Error", "Ingrese una cantidad válida")
                return
            
            cantidad = int(cantidad)
            
            # Generar timestamp
            now = datetime.now()
            timestamp = now.strftime("%d%m%y%H%M%S")
            
            # Generar códigos QR
            self.qr_codes = []
            for i in range(1, cantidad + 1):
                qr_text = f"{timestamp}_{destino}_{cliente}_{i}\n"
                
                # Crear QR
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_L,
                    box_size=10,
                    border=4,
                )
                qr.add_data(qr_text)
                qr.make(fit=True)
                
                # Crear imagen
                img = qr.make_image(fill_color="black", back_color="white")
                
                # Redimensionar para mostrar
                img = img.resize((300, 300), Image.Resampling.LANCZOS)
                
                # Convertir a PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                self.qr_codes.append({
                    'photo': photo,
                    'text': qr_text,
                    'numero': i
                })
            
            # Mostrar primer QR
            self.qr_actual = 0
            self.mostrar_qr_actual()
            
            # Habilitar navegación
            self.prev_button.configure(state="normal")
            self.next_button.configure(state="normal")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar códigos QR: {e}")
    
    def mostrar_qr_actual(self):
        """Muestra el QR actual"""
        if not self.qr_codes:
            return
        
        qr_data = self.qr_codes[self.qr_actual]
        
        # Mostrar imagen
        self.qr_label.configure(image=qr_data['photo'], text="")
        
        # Actualizar info
        total = len(self.qr_codes)
        self.qr_info_label.configure(text=f"{self.qr_actual + 1} de {total}")
        
        # Actualizar estado de botones
        self.prev_button.configure(state="disabled" if self.qr_actual == 0 else "normal")
        self.next_button.configure(state="disabled" if self.qr_actual == total - 1 else "normal")
    
    def qr_anterior(self):
        """Navega al QR anterior"""
        if self.qr_actual > 0:
            self.qr_actual -= 1
            self.mostrar_qr_actual()
    
    def qr_siguiente(self):
        """Navega al QR siguiente"""
        if self.qr_actual < len(self.qr_codes) - 1:
            self.qr_actual += 1
            self.mostrar_qr_actual()
    
    def create_configuracion_tab(self):
        """Crea la interfaz de configuración"""
        self.configuracion_frame.configure(bg="#f0f0f0")
        self.configuracion_frame.columnconfigure(0, weight=1)
        self.configuracion_frame.rowconfigure(0, weight=1)
        
        config_container = tk.Frame(self.configuracion_frame, bg="#f0f0f0", padx=20, pady=20)
        config_container.grid(row=0, column=0, sticky="nsew")
        
        # Frame de configuración
        ws_frame = tk.LabelFrame(
            config_container, 
            text="CONFIGURACIÓN DE DATOS", 
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 11, 'bold')
        )
        ws_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        ws_frame.columnconfigure(1, weight=1)
        ws_frame.columnconfigure(3, weight=1)
        
        # Motivos
        tk.Label(ws_frame, text="Motivos:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=5, sticky="nw"
        )
        
        self.motivos_text = tk.Text(ws_frame, width=30, height=8, font=('Helvetica', 10))
        self.motivos_text.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Destino
        tk.Label(ws_frame, text="Destino:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=2, padx=10, pady=5, sticky="nw"
        )
        
        self.destino_text = tk.Text(ws_frame, width=30, height=8, font=('Helvetica', 10))
        self.destino_text.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        # Clave Cliente
        tk.Label(ws_frame, text="Clave Cliente:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=1, column=0, padx=10, pady=5, sticky="nw"
        )
        
        self.clave_cliente_text = tk.Text(ws_frame, width=30, height=8, font=('Helvetica', 10))
        self.clave_cliente_text.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        
        # Botón Guardar
        save_button = customtkinter.CTkButton(
            ws_frame,
            text="Guardar Configuración",
            command=self.guardar_configuracion_manual,
            width=200,
            height=40,
            font=("Helvetica", 12, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        save_button.grid(row=1, column=2, columnspan=2, padx=10, pady=20)
        
        # Vincular eventos de cambio
        def update_motivos_var(event=None):
            self.motivos_var.set(self.motivos_text.get("1.0", "end-1c"))
        
        def update_destino_var(event=None):
            self.destino_var.set(self.destino_text.get("1.0", "end-1c"))
        
        def update_clave_cliente_var(event=None):
            self.clave_cliente_var.set(self.clave_cliente_text.get("1.0", "end-1c"))
        
        self.motivos_text.bind("<KeyRelease>", update_motivos_var)
        self.destino_text.bind("<KeyRelease>", update_destino_var)
        self.clave_cliente_text.bind("<KeyRelease>", update_clave_cliente_var)
    
    def guardar_configuracion_manual(self):
        """Guarda la configuración manualmente"""
        self.guardar_configuracion()
        self.actualizar_comboboxes()
        messagebox.showinfo("Éxito", "Configuración guardada correctamente")
    
    def cargar_configuracion(self):
        """Carga la configuración desde archivo"""
        config = configparser.ConfigParser()
        try:
            config.read('configuracion.ini')
            if 'Configuracion' in config:
                # Cargar motivos
                motivos_guardados = self.desencriptar(config['Configuracion'].get('motivos_var', ''))
                if motivos_guardados:
                    self.motivos_var.set(motivos_guardados)
                
                # Cargar destino
                destino_guardado = self.desencriptar(config['Configuracion'].get('destino_var', ''))
                if destino_guardado:
                    self.destino_var.set(destino_guardado)
                
                # Cargar clave cliente
                clave_cliente_guardada = self.desencriptar(config['Configuracion'].get('clave_cliente_var', ''))
                if clave_cliente_guardada:
                    self.clave_cliente_var.set(clave_cliente_guardada)
                
                # Actualizar widgets después de crear la interfaz
                self.root.after(500, self.actualizar_texto_configuracion)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar configuración: {e}")

    def actualizar_texto_configuracion(self):
        """Actualiza los widgets de texto con los valores cargados"""
        if hasattr(self, 'motivos_text'):
            self.motivos_text.delete("1.0", tk.END)
            self.motivos_text.insert("1.0", self.motivos_var.get())
        
        if hasattr(self, 'destino_text'):
            self.destino_text.delete("1.0", tk.END)
            self.destino_text.insert("1.0", self.destino_var.get())
        
        if hasattr(self, 'clave_cliente_text'):
            self.clave_cliente_text.delete("1.0", tk.END)
            self.clave_cliente_text.insert("1.0", self.clave_cliente_var.get())
        
        # Actualizar comboboxes
        self.actualizar_comboboxes()

    def guardar_configuracion(self):
        """Guarda la configuración en archivo"""
        config = configparser.ConfigParser()
        if not config.has_section('Configuracion'):
            config.add_section('Configuracion')
        
        # Actualizar variables con el contenido actual de los widgets
        if hasattr(self, 'motivos_text'):
            motivos_texto = self.motivos_text.get("1.0", "end-1c")
            self.motivos_var.set(motivos_texto)
        
        if hasattr(self, 'destino_text'):
            destino_texto = self.destino_text.get("1.0", "end-1c")
            self.destino_var.set(destino_texto)
        
        if hasattr(self, 'clave_cliente_text'):
            clave_cliente_texto = self.clave_cliente_text.get("1.0", "end-1c")
            self.clave_cliente_var.set(clave_cliente_texto)
        
        # Guardar valores encriptados
        config['Configuracion']['motivos_var'] = self.encriptar(self.motivos_var.get())
        config['Configuracion']['destino_var'] = self.encriptar(self.destino_var.get())
        config['Configuracion']['clave_cliente_var'] = self.encriptar(self.clave_cliente_var.get())
        
        # Guardar último puerto si existe
        if hasattr(self, 'puertos_combobox'):
            ultimo_puerto = self.puertos_combobox.get()
            config['Configuracion']['ultimo_puerto'] = self.encriptar(ultimo_puerto)
        
        try:
            with open('configuracion.ini', 'w') as configfile:
                config.write(configfile)
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar configuración: {e}")
    
    def encriptar(self, valor):
        """Cifra el valor utilizando la clave de cifrado"""
        if not valor:
            valor = ""
        return fernet.encrypt(valor.encode()).decode()

    def desencriptar(self, valor_cifrado):
        """Descifra el valor utilizando la clave de cifrado"""
        if not valor_cifrado:
            return ""
        try:
            token = valor_cifrado.encode()
            return fernet.decrypt(token).decode()
        except:
            return ""

if __name__ == "__main__":
    # Configurar tema de customtkinter
    customtkinter.set_appearance_mode("Dark")
    customtkinter.set_default_color_theme("blue")
    
    # Verificar que existe la base de datos encriptada
    if not os.path.exists("Montradb.db"):
        messagebox.showerror("Error", "No se encuentra la base de datos encriptada 'Montradb.db'")
        exit()
    
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