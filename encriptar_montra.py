from cryptography.fernet import Fernet
import sqlite3
import os
import json

class MontraEncriptada:
    def __init__(self, password):
        # Generar clave desde password
        import hashlib
        key = hashlib.sha256(password.encode()).digest()
        import base64
        self.key = base64.urlsafe_b64encode(key)
        self.cipher = Fernet(self.key)
    
    def encriptar_base(self, archivo_original, archivo_encriptado):
        """Encripta toda la base de datos"""
        try:
            # Leer el archivo original
            with open(archivo_original, 'rb') as f:
                datos_originales = f.read()
            
            # Encriptar
            datos_encriptados = self.cipher.encrypt(datos_originales)
            
            # Guardar archivo encriptado
            with open(archivo_encriptado, 'wb') as f:
                f.write(datos_encriptados)
            
            print(f"✅ Base encriptada guardada como: {archivo_encriptado}")
            return True
            
        except Exception as e:
            print(f"❌ Error al encriptar: {e}")
            return False
    
    def desencriptar_base(self, archivo_encriptado, archivo_temporal):
        """Desencripta la base para uso temporal"""
        try:
            # Leer archivo encriptado
            with open(archivo_encriptado, 'rb') as f:
                datos_encriptados = f.read()
            
            # Desencriptar
            datos_originales = self.cipher.decrypt(datos_encriptados)
            
            # Guardar temporalmente
            with open(archivo_temporal, 'wb') as f:
                f.write(datos_originales)
            
            return True
            
        except Exception as e:
            print(f"❌ Error al desencriptar: {e}")
            return False
    
    def conectar_seguro(self, archivo_encriptado):
        """Conecta a la base encriptada de forma segura"""
        archivo_temporal = "temp_montra.db"
        
        try:
            # Desencriptar temporalmente
            if self.desencriptar_base(archivo_encriptado, archivo_temporal):
                # Conectar a la base temporal
                conn = sqlite3.connect(archivo_temporal)
                return conn, archivo_temporal
            else:
                return None, None
                
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            return None, None
    
    def cerrar_seguro(self, conn, archivo_temporal):
        """Cierra la conexión y limpia archivos temporales"""
        if conn:
            conn.close()
        
        # Eliminar archivo temporal
        if os.path.exists(archivo_temporal):
            os.remove(archivo_temporal)
            print("🗑️ Archivo temporal eliminado")

# Script para encriptar Montra.DB
def encriptar_montra():
    password = input("Ingresa la contraseña para encriptar: ")
    
    # Crear instancia
    encriptador = MontraEncriptada(password)
    
    # Encriptar
    if encriptador.encriptar_base("Montra.DB", "Montra_Encriptada.db"):
        print("🎉 ¡Encriptación completada!")
        print("🔑 Guarda bien tu contraseña")
        
        # Guardar info de verificación (opcional)
        info = {
            "archivo_original": "Montra.DB",
            "archivo_encriptado": "Montra_Encriptada.db",
            "fecha_encriptacion": "2025-07-14"
        }
        
        with open("info_encriptacion.json", "w") as f:
            json.dump(info, f, indent=2)
        
        print("📄 Información guardada en info_encriptacion.json")
    else:
        print("❌ Error en la encriptación")

if __name__ == "__main__":
    encriptar_montra()