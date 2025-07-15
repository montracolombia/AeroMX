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
from tkcalendar import DateEntry
import barcode
from barcode.writer import ImageWriter

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
            
            # Crear tabla Registros si no existe
            self.crear_tabla_registros()
            
            return True
            
        except Exception as e:
            print(f"Error al conectar: {e}")
            return False
    
    def crear_tabla_registros(self):
        """Crea la tabla Registros si no existe"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS Registros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Recibo TEXT NOT NULL,
                    Codigo TEXT NOT NULL,
                    Fecha TEXT NOT NULL,
                    Hora TEXT NOT NULL
                )
            ''')
            self.conn.commit()
        except Exception as e:
            print(f"Error al crear tabla Registros: {e}")
    
    def guardar_registro(self, recibo, codigo, fecha, hora):
        """Guarda un registro en la base de datos"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO Registros (Recibo, Codigo, Fecha, Hora)
                VALUES (?, ?, ?, ?)
            ''', (recibo, codigo, fecha, hora))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error al guardar registro: {e}")
            return False
    
    def buscar_registros(self, recibo=None, fecha=None):
        """Busca registros por filtros"""
        try:
            cursor = self.conn.cursor()
            query = "SELECT Recibo, Codigo, Fecha, Hora FROM Registros WHERE 1=1"
            params = []
            
            if recibo:
                query += " AND Recibo LIKE ?"
                params.append(f"%{recibo}%")
            
            if fecha:
                query += " AND Fecha = ?"
                params.append(fecha)
            
            query += " ORDER BY Fecha DESC, Hora DESC"
            
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            print(f"Error al buscar registros: {e}")
            return []
    
    def guardar_cambios_db(self):
        """Guarda los cambios de vuelta al archivo encriptado"""
        try:
            # Serializar base de datos desde memoria
            datos_actualizados = self.conn.serialize()
            
            # Encriptar
            datos_encriptados = self.cipher.encrypt(datos_actualizados)
            
            # Guardar
            with open(self.archivo_encriptado, 'wb') as f:
                f.write(datos_encriptados)
            
            return True
        except Exception as e:
            print(f"Error al guardar cambios en DB: {e}")
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
        self.destino_var = tk.StringVar(value="")
        self.clave_cliente_var = tk.StringVar(value="")
        self.tipo_codigo_var = tk.StringVar(value="QR")
        
        # Variables para QR
        self.qr_codes = []
        self.qr_actual = 0
        self.recibo_actual = ""
        
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
        self.busqueda_frame = tk.Frame(self.content_container, bg="#f0f0f0")
        self.configuracion_frame = tk.Frame(self.content_container, bg="#f0f0f0")
        
        # Cargar imágenes
        self.imagenes()
        
        # Crear la barra lateral con los botones
        self.create_sidebar()
        
        # Crear contenido de las secciones
        self.create_configuracion_tab()
        self.create_busqueda_tab()
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
        
        # Botón de Búsqueda
        self.busqueda_button = customtkinter.CTkButton(
            self.sidebar, 
            text="BÚSQUEDA",
            command=self.show_busqueda,
            **button_style
        )
        self.busqueda_button.pack(padx=10, pady=10)
        
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
        self.busqueda_frame.pack_forget()
        self.configuracion_frame.pack_forget()
        self.medicion_frame.pack(fill="both", expand=True, padx=10)
        self.medicion_button.configure(fg_color="#1f5c87")
        self.busqueda_button.configure(fg_color=self.color_botones)
        self.configuracion_button.configure(fg_color=self.color_botones)

    def show_busqueda(self):
        """Muestra el panel de búsqueda"""
        self.medicion_frame.pack_forget()
        self.configuracion_frame.pack_forget()
        self.busqueda_frame.pack(fill="both", expand=True, padx=10)
        self.busqueda_button.configure(fg_color="#1f5c87")
        self.medicion_button.configure(fg_color=self.color_botones)
        self.configuracion_button.configure(fg_color=self.color_botones)

    def show_configuracion(self):
        """Muestra el panel de configuración después de verificar credenciales"""
        self.login_window = tk.Toplevel(self.root)
        self.login_window.title("Acceso")
        
        # Ventana más grande
        position_x = int(self.root.winfo_x() + (self.root.winfo_width() / 2) - (300 / 2))
        position_y = int(self.root.winfo_y() + (self.root.winfo_height() / 2) - (250 / 2))
        self.login_window.geometry(f"{300}x{250}+{position_x}+{position_y}")
        self.login_window.resizable(False, False)
        self.login_window.attributes("-topmost", True)
        self.login_window.configure(bg="#f0f0f0")
        
        # Agregar icono
        try:
            self.login_window.iconbitmap("Icons/montra.ico")
        except:
            pass
        
        login_frame = tk.Frame(self.login_window, bg="#f0f0f0", padx=30, pady=30)
        login_frame.pack(fill="both", expand=True)
        login_frame.columnconfigure(0, weight=1)

        # Container para campos
        campos_container = tk.Frame(login_frame, bg="#f0f0f0")
        campos_container.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        campos_container.columnconfigure(0, weight=1)
        
        # Usuario
        username_label = tk.Label(
            campos_container, 
            text="Usuario:", 
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0",
            anchor="w"
        )
        username_label.grid(row=0, column=0, sticky="w", pady=(0, 5))
        
        username_var = tk.StringVar()
        username_entry = ttk.Entry(
            campos_container, 
            textvariable=username_var,
            font=("Helvetica", 12),
            width=30
        )
        username_entry.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        username_entry.focus_set()
        
        # Contraseña
        password_label = tk.Label(
            campos_container, 
            text="Contraseña:", 
            font=("Helvetica", 12, "bold"),
            bg="#f0f0f0",
            anchor="w"
        )
        password_label.grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        password_var = tk.StringVar()
        password_entry = ttk.Entry(
            campos_container, 
            textvariable=password_var,
            show="*", 
            font=("Helvetica", 12),
            width=30
        )
        password_entry.grid(row=3, column=0, sticky="ew")
        
        def check_credentials_local():
            username = username_var.get()
            password = password_var.get()
            if self.db.verificar_credenciales(username, password):
                self.login_window.destroy()
                self.medicion_frame.pack_forget()
                self.busqueda_frame.pack_forget()
                self.configuracion_frame.pack(fill="both", expand=True)
                self.configuracion_button.configure(fg_color="#1f5c87")
                self.medicion_button.configure(fg_color=self.color_botones)
                self.busqueda_button.configure(fg_color=self.color_botones)
            else:
                self.login_window.destroy()
                messagebox.showerror("Acceso denegado", "Credenciales incorrectas")
        
        # Botón Ingresar - MÁS GRANDE
        login_button = customtkinter.CTkButton(
            login_frame,
            text="Ingresar",
            font=("Helvetica", 12, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b",
            height=40,
            width=200,
            command=check_credentials_local
        )
        login_button.grid(row=3, column=0, pady=20)
        
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

    def filtrar_combobox(self, event, combobox, values):
        """Filtra los valores del combobox - búsqueda simple sin interrupciones"""
        typed = event.widget.get().lower()
        
        if typed == '':
            # Si está vacío, mostrar todas las opciones
            combobox['values'] = values
        else:
            # Filtrar opciones que contengan el texto escrito
            filtered = [item for item in values if typed in item.lower()]
            combobox['values'] = filtered
        
        # NO abrir la lista automáticamente para permitir escritura continua

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
        
        # Frame de configuración - MEJORADO Y SIMÉTRICO
        config_frame = tk.LabelFrame(
            main_container,
            text="CONFIGURACIÓN DE LA ORDEN",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold')
        )
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        # Configurar grid del config_frame para distribución simétrica
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(2, weight=1)
        
        # Container para los campos (más organizado)
        campos_container = tk.Frame(config_frame, bg="#f0f0f0")
        campos_container.grid(row=0, column=0, columnspan=3, sticky="ew", padx=20, pady=15)
        campos_container.columnconfigure(0, weight=1)
        campos_container.columnconfigure(1, weight=1)
        campos_container.columnconfigure(2, weight=1)
        
        # Destino
        destino_frame = tk.Frame(campos_container, bg="#f0f0f0")
        destino_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        
        tk.Label(destino_frame, text="Destino:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).pack(anchor="w")
        self.destino_combo = ttk.Combobox(destino_frame, font=('Helvetica', 11))
        self.destino_combo.pack(fill="x", pady=(5, 0))
        
        # Cliente
        cliente_frame = tk.Frame(campos_container, bg="#f0f0f0")
        cliente_frame.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        tk.Label(cliente_frame, text="Cliente:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).pack(anchor="w")
        self.cliente_combo = ttk.Combobox(cliente_frame, font=('Helvetica', 11))
        self.cliente_combo.pack(fill="x", pady=(5, 0))
        
        # Cantidad de Pallets - MÁS PEQUEÑO
        cantidad_frame = tk.Frame(campos_container, bg="#f0f0f0")
        cantidad_frame.grid(row=0, column=2, padx=10, pady=5, sticky="ew")
        
        tk.Label(cantidad_frame, text="Cantidad de Pallets:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).pack(anchor="w")
        
        # Validación para solo números
        def validar_numero(char):
            return char.isdigit()
        
        vcmd = (self.root.register(validar_numero), '%S')
        
        # Entry más pequeño para cantidad
        cantidad_container = tk.Frame(cantidad_frame, bg="#f0f0f0")
        cantidad_container.pack(fill="x", pady=(5, 0))
        
        self.cantidad_entry = tk.Entry(cantidad_container, font=('Helvetica', 11), validate='key', validatecommand=vcmd, width=10)
        self.cantidad_entry.pack(side="left")
        
        # Botón Generar - CENTRADO
        button_container = tk.Frame(config_frame, bg="#f0f0f0")
        button_container.grid(row=1, column=0, columnspan=3, pady=20)
        
        self.generar_button = customtkinter.CTkButton(
            button_container,
            text="Generar Códigos",
            command=self.generar_qr_codes,
            width=250,
            height=45,
            font=("Helvetica", 13, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        self.generar_button.pack()
        
        # Frame para mostrar QR
        self.qr_frame = tk.LabelFrame(
            main_container,
            text="CÓDIGOS GENERADOS",
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
        qr_container.rowconfigure(0, weight=1)
        
        # Label para mostrar QR
        self.qr_label = tk.Label(qr_container, bg="#f0f0f0", text="Genere códigos para visualizar")
        self.qr_label.grid(row=0, column=0, pady=10, sticky="nsew")
        
        # Frame de navegación - CENTRADO Y OCULTO INICIALMENTE
        self.nav_frame = tk.Frame(qr_container, bg="#f0f0f0")
        # NO hacer grid inicialmente - estará oculto
        
        # Botones de navegación
        self.prev_button = customtkinter.CTkButton(
            self.nav_frame,
            text="◀ Anterior",
            command=self.qr_anterior,
            width=100,
            height=30,
            font=("Helvetica", 10),
            fg_color="#4a636f",
            hover_color="#5b7684"
        )
        self.prev_button.pack(side="left", padx=5)
        
        self.qr_info_label = tk.Label(self.nav_frame, text="", bg="#f0f0f0", font=('Helvetica', 11, 'bold'))
        self.qr_info_label.pack(side="left", padx=20)
        
        self.next_button = customtkinter.CTkButton(
            self.nav_frame,
            text="Siguiente ▶",
            command=self.qr_siguiente,
            width=100,
            height=30,
            font=("Helvetica", 10),
            fg_color="#4a636f",
            hover_color="#5b7684"
        )
        self.next_button.pack(side="left", padx=5)
        
        # Frame de recibo - MÁS COMPACTO
        self.recibo_frame = tk.LabelFrame(
            main_container,
            text="RECIBO",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold'),
            height=120
        )
        # No hacer grid inicialmente
        
        # Contenido del frame de recibo - MÁS COMPACTO
        recibo_container = tk.Frame(self.recibo_frame, bg="#f0f0f0")
        recibo_container.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        recibo_container.columnconfigure(1, weight=1)
        recibo_container.columnconfigure(3, weight=1)
        
        # Primera verificación
        tk.Label(recibo_container, text="Verificación:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        
        self.verif1_entry = tk.Entry(recibo_container, width=20, font=('Helvetica', 11))
        self.verif1_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Segunda verificación
        tk.Label(recibo_container, text="Confirmar:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=2, padx=10, pady=5, sticky="w"
        )
        
        self.verif2_entry = tk.Entry(recibo_container, width=20, font=('Helvetica', 11))
        self.verif2_entry.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        # Botón Cerrar Orden
        self.cerrar_orden_button = customtkinter.CTkButton(
            recibo_container,
            text="Cerrar Orden",
            command=self.cerrar_orden,
            width=150,
            height=35,
            font=("Helvetica", 11, "bold"),
            fg_color="#d32f2f",
            hover_color="#b71c1c"
        )
        self.cerrar_orden_button.grid(row=1, column=0, columnspan=4, pady=5)
        
        # Deshabilitar copiar/pegar en los campos de verificación
        def bloquear_paste(event):
            return "break"
        
        self.verif1_entry.bind("<Control-v>", bloquear_paste)
        self.verif1_entry.bind("<Control-V>", bloquear_paste)
        self.verif1_entry.bind("<Button-3>", bloquear_paste)
        
        self.verif2_entry.bind("<Control-v>", bloquear_paste)
        self.verif2_entry.bind("<Control-V>", bloquear_paste)
        self.verif2_entry.bind("<Button-3>", bloquear_paste)
        
        # Configurar pesos para que QR se expanda pero recibo sea compacto
        main_container.rowconfigure(1, weight=3)
        main_container.rowconfigure(2, weight=0)
        
        # Actualizar comboboxes
        self.actualizar_comboboxes()

    def create_busqueda_tab(self):
        """Crea la interfaz de búsqueda"""
        self.busqueda_frame.configure(bg="#f0f0f0")
        self.busqueda_frame.columnconfigure(0, weight=1)
        self.busqueda_frame.rowconfigure(0, weight=1)
        
        # Contenedor principal
        busqueda_container = tk.Frame(self.busqueda_frame, bg="#f0f0f0", padx=20, pady=20)
        busqueda_container.grid(row=0, column=0, sticky="nsew")
        busqueda_container.columnconfigure(0, weight=1)
        busqueda_container.rowconfigure(1, weight=1)
        
        # Frame de filtros
        filtros_frame = tk.LabelFrame(
            busqueda_container,
            text="FILTROS DE BÚSQUEDA",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold')
        )
        filtros_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        filtros_frame.columnconfigure(1, weight=1)
        filtros_frame.columnconfigure(3, weight=1)
        
        # Filtro por Recibo
        tk.Label(filtros_frame, text="Recibo:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        
        self.filtro_recibo_entry = tk.Entry(filtros_frame, width=25, font=('Helvetica', 11))
        self.filtro_recibo_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        # Filtro por Fecha - CON CALENDARIO MEJORADO
        tk.Label(filtros_frame, text="Fecha:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=2, padx=10, pady=10, sticky="w"
        )
        
        # Crear Entry manual para fecha vacía inicialmente
        self.filtro_fecha_entry = tk.Entry(filtros_frame, width=15, font=('Helvetica', 11))
        self.filtro_fecha_entry.grid(row=0, column=3, padx=10, pady=10, sticky="ew")
        
        # Botón para abrir calendario
        self.calendario_button = tk.Button(
            filtros_frame,
            text="📅",
            font=('Helvetica', 8),
            width=3,
            command=self.abrir_calendario
        )
        self.calendario_button.grid(row=0, column=4, padx=(0, 10), pady=10)
        
        # Botones
        botones_frame = tk.Frame(filtros_frame, bg="#f0f0f0")
        botones_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        self.buscar_button = customtkinter.CTkButton(
            botones_frame,
            text="Buscar",
            command=self.buscar_registros,
            width=120,
            height=35,
            font=("Helvetica", 11, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        self.buscar_button.pack(side="left", padx=5)
        
        self.limpiar_filtros_button = customtkinter.CTkButton(
            botones_frame,
            text="Limpiar",
            command=self.limpiar_filtros,
            width=120,
            height=35,
            font=("Helvetica", 11, "bold"),
            fg_color="#4a636f",
            hover_color="#5b7684"
        )
        self.limpiar_filtros_button.pack(side="left", padx=5)
        
        # Frame de resultados
        resultados_frame = tk.LabelFrame(
            busqueda_container,
            text="RESULTADOS",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 12, 'bold')
        )
        resultados_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        resultados_frame.columnconfigure(0, weight=1)
        resultados_frame.rowconfigure(0, weight=1)
        
        # Treeview para mostrar resultados
        tree_frame = tk.Frame(resultados_frame, bg="#f0f0f0")
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Configurar Treeview con estilo
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview.Heading", 
                       background="#1f5c87", 
                       foreground="white", 
                       font=('Helvetica', 11, 'bold'))
        style.configure("Treeview", 
                       background="#f9f9f9",
                       foreground="black",
                       rowheight=25,
                       fieldbackground="#f9f9f9")
        style.map("Treeview", 
                 background=[('selected', '#347dba')])
        
        columns = ("Recibo", "Código", "Fecha", "Hora")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
        
        # Configurar columnas
        self.tree.heading("Recibo", text="Recibo")
        self.tree.heading("Código", text="Código")
        self.tree.heading("Fecha", text="Fecha")
        self.tree.heading("Hora", text="Hora")
        
        self.tree.column("Recibo", width=200)
        self.tree.column("Código", width=300)
        self.tree.column("Fecha", width=120)
        self.tree.column("Hora", width=120)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid del Treeview y scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Label para mostrar cantidad de resultados
        self.resultados_label = tk.Label(
            resultados_frame,
            text="",
            bg="#f0f0f0",
            font=('Helvetica', 10),
            fg="#666666"
        )
        self.resultados_label.grid(row=1, column=0, pady=5)

    def abrir_calendario(self):
        """Abre una ventana de calendario moderna para seleccionar fecha"""
        calendario_window = tk.Toplevel(self.root)
        calendario_window.title("Seleccionar Fecha")
        calendario_window.geometry("300x350")
        calendario_window.resizable(False, False)
        calendario_window.configure(bg="#f0f0f0")
        calendario_window.attributes("-topmost", True)
        
        # Agregar icono
        try:
            calendario_window.iconbitmap("Icons/montra.ico")
        except:
            pass
        
        # Posicionar debajo del campo de fecha
        filtro_x = self.filtro_fecha_entry.winfo_rootx()
        filtro_y = self.filtro_fecha_entry.winfo_rooty() + self.filtro_fecha_entry.winfo_height() + 5
        calendario_window.geometry(f"300x350+{filtro_x}+{filtro_y}")
        
        
        # Contenedor principal
        main_frame = tk.Frame(calendario_window, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Crear calendario con estilo moderno
        from tkcalendar import Calendar
        cal = Calendar(
            main_frame,
            selectmode='day',
            date_pattern='dd-mm-yyyy',
            background='#1f5c87',
            foreground='white',
            borderwidth=0,
            headersbackground='#144a6b',
            headersforeground='white',
            selectbackground='#347dba',
            selectforeground='white',
            normalbackground='#f0f0f0',
            normalforeground='black',
            weekendbackground='#e8e8e8',
            weekendforeground='#666666',
            font=('Helvetica', 10),
            bordercolor='#1f5c87'
        )
        cal.pack(padx=10, pady=10, fill="both", expand=True)
        
        # Frame para botones con estilo moderno
        button_frame = tk.Frame(main_frame, bg="#f0f0f0")
        button_frame.pack(pady=20)
        
        def seleccionar_fecha():
            fecha_seleccionada = cal.get_date()
            # Convertir de dd-mm-yyyy a yyyy-mm-dd para la base de datos
            try:
                from datetime import datetime
                fecha_obj = datetime.strptime(fecha_seleccionada, '%d-%m-%Y')
                fecha_bd = fecha_obj.strftime('%Y-%m-%d')
                
                # Mostrar en formato dd-mm-yyyy en el campo
                self.filtro_fecha_entry.delete(0, tk.END)
                self.filtro_fecha_entry.insert(0, fecha_seleccionada)
                # Guardar formato BD para búsqueda
                self.fecha_bd_formato = fecha_bd
                
                calendario_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error al procesar fecha: {e}")
        
        def cancelar():
            calendario_window.destroy()
        
        # Botones modernos
        seleccionar_btn = customtkinter.CTkButton(
            button_frame,
            text="Seleccionar",
            command=seleccionar_fecha,
            width=120,
            height=35,
            font=("Helvetica", 11, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        seleccionar_btn.pack(side="left", padx=10)
        
        cancelar_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancelar",
            command=cancelar,
            width=120,
            height=35,
            font=("Helvetica", 11, "bold"),
            fg_color="#666666",
            hover_color="#555555"
        )
        cancelar_btn.pack(side="left", padx=10)
        
        # Enfocar la ventana
        calendario_window.focus_set()
        calendario_window.grab_set()

    def buscar_registros(self):
        """Realiza la búsqueda de registros"""
        recibo = self.filtro_recibo_entry.get().strip()
        
        # Obtener fecha
        fecha_para_busqueda = None
        fecha_texto = self.filtro_fecha_entry.get().strip()
        
        if fecha_texto:
            try:
                # Si hay fecha, usar el formato de BD guardado
                if hasattr(self, 'fecha_bd_formato'):
                    fecha_para_busqueda = self.fecha_bd_formato
                else:
                    # Intentar convertir manualmente si se escribió
                    from datetime import datetime
                    fecha_obj = datetime.strptime(fecha_texto, '%d-%m-%Y')
                    fecha_para_busqueda = fecha_obj.strftime('%Y-%m-%d')
            except:
                # Si no se puede convertir, buscar sin fecha
                fecha_para_busqueda = None
                messagebox.showwarning("Advertencia", "Formato de fecha incorrecto. Use dd-mm-yyyy o seleccione del calendario.")
        
        # Limpiar resultados anteriores
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Buscar en la base de datos
        resultados = self.db.buscar_registros(recibo if recibo else None, fecha_para_busqueda)
        
        # Mostrar resultados
        for registro in resultados:
            self.tree.insert("", "end", values=registro)
        
        # Actualizar label de resultados
        self.resultados_label.configure(text=f"Se encontraron {len(resultados)} registros")
        
        if len(resultados) == 0:
            messagebox.showinfo("Búsqueda", "No se encontraron registros con los filtros especificados")

    def limpiar_filtros(self):
        """Limpia los filtros de búsqueda"""
        self.filtro_recibo_entry.delete(0, tk.END)
        self.filtro_fecha_entry.delete(0, tk.END)
        # Limpiar también el formato BD guardado
        if hasattr(self, 'fecha_bd_formato'):
            delattr(self, 'fecha_bd_formato')
        
        # Limpiar resultados
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.resultados_label.configure(text="")
    
    def validar_sin_tildes(self, char):
        """Valida que no se ingresen tildes ni caracteres especiales"""
        tildes = 'áéíóúÁÉÍÓÚñÑ'
        return char not in tildes
    
    def actualizar_comboboxes(self):
        """Actualiza los comboboxes con los valores de configuración"""
        # Destino
        destinos = self.destino_var.get().split('\n') if self.destino_var.get() else []
        destinos = [d.strip() for d in destinos if d.strip()]
        
        # Cliente
        clientes = self.clave_cliente_var.get().split('\n') if self.clave_cliente_var.get() else []
        clientes = [c.strip() for c in clientes if c.strip()]
        
        # Actualizar valores de comboboxes si existen
        if hasattr(self, 'destino_combo'):
            self.destino_combo['values'] = destinos
            
            # Configurar validación para no tildes
            vcmd_destino = (self.root.register(self.validar_sin_tildes), '%S')
            self.destino_combo.configure(validate='key', validatecommand=vcmd_destino)
        
        if hasattr(self, 'cliente_combo'):
            self.cliente_combo['values'] = clientes
            
            # Configurar validación para no tildes
            vcmd_cliente = (self.root.register(self.validar_sin_tildes), '%S')
            self.cliente_combo.configure(validate='key', validatecommand=vcmd_cliente)
        
        # Configurar autocompletado simple
        if hasattr(self, 'destino_combo'):
            # Limpiar eventos anteriores
            self.destino_combo.unbind('<KeyRelease>')
            # Vincular evento simple
            self.destino_combo.bind('<KeyRelease>', lambda e: self.filtrar_combobox(e, self.destino_combo, destinos))
        
        if hasattr(self, 'cliente_combo'):
            # Limpiar eventos anteriores
            self.cliente_combo.unbind('<KeyRelease>')
            # Vincular evento simple
            self.cliente_combo.bind('<KeyRelease>', lambda e: self.filtrar_combobox(e, self.cliente_combo, clientes))
    
    def generar_qr_codes(self):
        """Genera los códigos QR o de barras según la configuración"""
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
            
            # Generar timestamp y recibo único
            now = datetime.now()
            timestamp = now.strftime("%d%m%y%H%M%S")
            self.recibo_actual = f"{timestamp}_{destino}_{cliente}"
            
            # Generar códigos según tipo configurado
            self.qr_codes = []
            tipo_codigo = self.tipo_codigo_var.get()
            
            for i in range(1, cantidad + 1):
                codigo_text = f"{timestamp}_{destino}_{cliente}_{i}"
                
                if tipo_codigo == "QR":
                    # Crear QR
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(codigo_text)
                    qr.make(fit=True)
                    
                    # Crear imagen
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                else:  # BARCODE
                    # Crear código de barras (Code128)
                    try:
                        code128 = barcode.get_barcode_class('code128')
                        barcode_instance = code128(codigo_text, writer=ImageWriter())
                        
                        # Crear imagen del código de barras
                        img = barcode_instance.render()
                        
                    except Exception as e:
                        messagebox.showerror("Error", f"Error al generar código de barras: {e}")
                        return
                
                # Redimensionar para mostrar
                if tipo_codigo == "QR":
                    img = img.resize((300, 300), Image.Resampling.LANCZOS)
                else:
                    # Para códigos de barras, ajustar proporcionalmente
                    img = img.resize((400, 200), Image.Resampling.LANCZOS)
                
                # Convertir a PhotoImage
                photo = ImageTk.PhotoImage(img)
                
                self.qr_codes.append({
                    'photo': photo,
                    'text': codigo_text,
                    'numero': i,
                    'codigo': codigo_text,
                    'tipo': tipo_codigo
                })
            
            # Mostrar primer código
            self.qr_actual = 0
            self.mostrar_qr_actual()
            
            # MOSTRAR las flechas de navegación
            self.nav_frame.grid(row=1, column=0, pady=5)
            
            # Mostrar frame de recibo
            self.recibo_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(5, 10))
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar códigos: {e}")
    
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
    
    def cerrar_orden(self):
        """Cierra la orden verificando que los campos coincidan y guarda en DB"""
        verif1 = self.verif1_entry.get().strip()
        verif2 = self.verif2_entry.get().strip()
        
        if not verif1 or not verif2:
            messagebox.showerror("Error", "Debe llenar ambos campos de verificación")
            return
        
        if verif1 != verif2:
            messagebox.showerror("Error", "Los valores de verificación no coinciden")
            return
        
        # Guardar registros en la base de datos
        try:
            now = datetime.now()
            fecha = now.strftime("%Y-%m-%d")
            hora = now.strftime("%H:%M:%S")
            
            registros_guardados = 0
            
            # Guardar cada QR como un registro separado
            for qr_data in self.qr_codes:
                if self.db.guardar_registro(
                    recibo=verif1,
                    codigo=qr_data['codigo'],
                    fecha=fecha,
                    hora=hora
                ):
                    registros_guardados += 1
            
            # Guardar cambios en archivo encriptado
            self.db.guardar_cambios_db()
            
            # Limpiar campos
            self.limpiar_campos()
            messagebox.showinfo("Éxito", f"Orden cerrada correctamente. {registros_guardados} registros guardados.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar registros: {e}")
    
    def limpiar_campos(self):
        """Limpia todos los campos para un nuevo registro"""
        # Limpiar comboboxes
        self.destino_combo.set("")
        self.cliente_combo.set("")
        
        # Limpiar cantidad
        self.cantidad_entry.delete(0, tk.END)
        
        # Limpiar verificaciones
        self.verif1_entry.delete(0, tk.END)
        self.verif2_entry.delete(0, tk.END)
        
        # Ocultar frame de recibo
        self.recibo_frame.grid_forget()
        
        # OCULTAR las flechas de navegación
        self.nav_frame.grid_forget()
        
        # Limpiar QR
        self.qr_codes = []
        self.qr_actual = 0
        self.recibo_actual = ""
        self.qr_label.configure(image="", text="Códigos a visualizar")
        self.qr_info_label.configure(text="")
    
    def create_configuracion_tab(self):
        
        self.carpeta_imagenes = tk.StringVar()
        """Crea la interfaz de configuración"""
        self.configuracion_frame.configure(bg="#f0f0f0")
        self.configuracion_frame.columnconfigure(0, weight=1)
        self.configuracion_frame.rowconfigure(0, weight=1)
        
        config_container = tk.Frame(self.configuracion_frame, bg="#f0f0f0", padx=20, pady=20)
        config_container.grid(row=0, column=0, sticky="nsew")
        
        # Frame de configuración de datos
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
        
        # Destino
        tk.Label(ws_frame, text="Destino:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=5, sticky="nw"
        )
        
        self.destino_text = tk.Text(ws_frame, width=40, height=10, font=('Helvetica', 10))
        self.destino_text.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        
        # Clave Cliente
        tk.Label(ws_frame, text="Clave Cliente:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=2, padx=10, pady=5, sticky="nw"
        )
        
        self.clave_cliente_text = tk.Text(ws_frame, width=40, height=10, font=('Helvetica', 10))
        self.clave_cliente_text.grid(row=0, column=3, padx=10, pady=5, sticky="ew")
        
        # Instrucciones
        instrucciones = tk.Label(
            ws_frame,
            text="Instrucciones: Ingrese cada elemento en una línea separada",
            bg="#f0f0f0",
            font=('Helvetica', 10, 'italic'),
            fg="#666666"
        )
        instrucciones.grid(row=1, column=0, columnspan=4, pady=10)
        
        # Frame de configuración de códigos
        tipo_codigo_frame = tk.LabelFrame(
            config_container,
            text="CONFIGURACIÓN DE CÓDIGOS",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 11, 'bold')
        )
        tipo_codigo_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        tk.Label(tipo_codigo_frame, text="Tipo de código a generar:", bg="#f0f0f0", font=('Helvetica', 11, 'bold')).grid(
            row=0, column=0, padx=10, pady=10, sticky="w"
        )
        
        # Checkbox para QR
        self.qr_var = tk.BooleanVar()
        self.qr_checkbox = tk.Checkbutton(
            tipo_codigo_frame,
            text="Códigos 2D (QR)",
            variable=self.qr_var,
            bg="#f0f0f0",
            font=('Helvetica', 10),
            command=self.on_qr_select
        )
        self.qr_checkbox.grid(row=1, column=0, padx=20, pady=5, sticky="w")
        
        # Checkbox para código de barras
        self.barcode_var = tk.BooleanVar()
        self.barcode_checkbox = tk.Checkbutton(
            tipo_codigo_frame,
            text="Códigos 1D (Lineales)",
            variable=self.barcode_var,
            bg="#f0f0f0",
            font=('Helvetica', 10),
            command=self.on_barcode_select
        )
        self.barcode_checkbox.grid(row=2, column=0, padx=20, pady=5, sticky="w")
        
        # Por defecto QR seleccionado
        self.qr_var.set(True)
        self.tipo_codigo_var.set("QR")
        
        # Botón Guardar
        save_button = customtkinter.CTkButton(
            config_container,
            text="Guardar Configuración",
            command=self.guardar_configuracion_manual,
            width=200,
            height=40,
            font=("Helvetica", 12, "bold"),
            fg_color="#1f5c87",
            hover_color="#144a6b"
        )
        save_button.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Frame de configuración de códigos
        carpeta_imagenes_frame= tk.LabelFrame(
            config_container,
            text="CARPETA DE IMÁGENES",
            labelanchor="nw",
            bg="#f0f0f0",
            font=('Helvetica', 11, 'bold')
        )
        carpeta_imagenes_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=10)
        
        tk.Label(carpeta_imagenes_frame, text="Ruta origen imágenes:", bg="#f0f0f0", font=('Helvetica', 11)).grid(
            row=0, column=0, padx=10, pady=5, sticky="w"
        )
        ruta_entry = ttk.Entry(carpeta_imagenes_frame, textvariable=self.carpeta_imagenes, width=30, font=('Helvetica', 11))
        ruta_entry.grid(row=0, column=1, padx=10, pady=5, sticky="w")

        # Botón seleccionar carpeta - estilo compatible con los botones de medición
        seleccionar_carpeta_button = customtkinter.CTkButton(
            carpeta_imagenes_frame,
            text="📁",
            corner_radius=8,
            font=("Helvetica", 14),
            fg_color="#1f5c87",
            hover_color="#164570",
            text_color="white",
            width=40,
            height=28,
            command=self.seleccionar_carpeta
        )
        seleccionar_carpeta_button.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        # Vincular eventos de cambio
        def update_destino_var(event=None):
            self.destino_var.set(self.destino_text.get("1.0", "end-1c"))
        
        def update_clave_cliente_var(event=None):
            self.clave_cliente_var.set(self.clave_cliente_text.get("1.0", "end-1c"))
        
        self.destino_text.bind("<KeyRelease>", update_destino_var)
        self.clave_cliente_text.bind("<KeyRelease>", update_clave_cliente_var)
    
    def seleccionar_carpeta(self):
        folder_selected = filedialog.askdirectory(title="Seleccione una carpeta de destino")
        if folder_selected:
            self.carpeta_imagenes.set(folder_selected)
            
        
    def on_qr_select(self):
        """Maneja la selección de QR"""
        if self.qr_var.get():
            self.barcode_var.set(False)
            self.tipo_codigo_var.set("QR")
    
    def on_barcode_select(self):
        """Maneja la selección de código de barras"""
        if self.barcode_var.get():
            self.qr_var.set(False)
            self.tipo_codigo_var.set("BARCODE")
    
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
                # Cargar destino
                destino_guardado = self.desencriptar(config['Configuracion'].get('destino_var', ''))
                if destino_guardado:
                    self.destino_var.set(destino_guardado)
                
                # Cargar clave cliente
                clave_cliente_guardada = self.desencriptar(config['Configuracion'].get('clave_cliente_var', ''))
                if clave_cliente_guardada:
                    self.clave_cliente_var.set(clave_cliente_guardada)
                
                # Cargar tipo de código
                tipo_codigo_guardado = self.desencriptar(config['Configuracion'].get('tipo_codigo_var', 'QR'))
                if tipo_codigo_guardado:
                    self.tipo_codigo_var.set(tipo_codigo_guardado)
                    
                carpeta_imagenes_guardada = self.desencriptar(config['Configuracion'].get('carpeta_imagenes', ''))
                if carpeta_imagenes_guardada:
                    self.carpeta_imagenes.set(carpeta_imagenes_guardada)
                
                # Actualizar widgets después de crear la interfaz
                self.root.after(500, self.actualizar_texto_configuracion)
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar configuración: {e}")

    def actualizar_texto_configuracion(self):
        """Actualiza los widgets de texto con los valores cargados"""
        if hasattr(self, 'destino_text'):
            self.destino_text.delete("1.0", tk.END)
            self.destino_text.insert("1.0", self.destino_var.get())
        
        if hasattr(self, 'clave_cliente_text'):
            self.clave_cliente_text.delete("1.0", tk.END)
            self.clave_cliente_text.insert("1.0", self.clave_cliente_var.get())
        
        # Actualizar checkboxes de tipo de código
        if hasattr(self, 'qr_var') and hasattr(self, 'barcode_var'):
            tipo_codigo = self.tipo_codigo_var.get()
            if tipo_codigo == "QR":
                self.qr_var.set(True)
                self.barcode_var.set(False)
            else:
                self.qr_var.set(False)
                self.barcode_var.set(True)
        
        # Actualizar comboboxes
        self.actualizar_comboboxes()

    def guardar_configuracion(self):
        """Guarda la configuración en archivo"""
        config = configparser.ConfigParser()
        if not config.has_section('Configuracion'):
            config.add_section('Configuracion')
        
        # Actualizar variables con el contenido actual de los widgets
        if hasattr(self, 'destino_text'):
            destino_texto = self.destino_text.get("1.0", "end-1c")
            self.destino_var.set(destino_texto)
        
        if hasattr(self, 'clave_cliente_text'):
            clave_cliente_texto = self.clave_cliente_text.get("1.0", "end-1c")
            self.clave_cliente_var.set(clave_cliente_texto)
        
        # Guardar valores encriptados
        config['Configuracion']['destino_var'] = self.encriptar(self.destino_var.get())
        config['Configuracion']['clave_cliente_var'] = self.encriptar(self.clave_cliente_var.get())
        config['Configuracion']['tipo_codigo_var'] = self.encriptar(self.tipo_codigo_var.get())
        config['Configuracion']['carpeta_imagenes'] = self.encriptar(self.carpeta_imagenes.get())
        
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
    
    # Verificar dependencias
    try:
        import tkcalendar
        import barcode
    except ImportError as e:
        missing_lib = str(e).split("'")[1]
        messagebox.showerror("Error", f"Falta instalar la librería: {missing_lib}\n\nEjecute: pip install {missing_lib}")
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