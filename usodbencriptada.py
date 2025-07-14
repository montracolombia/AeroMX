from cryptography.fernet import Fernet
import sqlite3
import hashlib
import base64
import io

class MontraManager:
    def __init__(self, archivo_encriptado="Montra_Encriptada.db", password=None):
        self.archivo_encriptado = archivo_encriptado
        self.conn = None
        self.datos_en_memoria = None
        
        if password:
            # Generar clave desde password
            key = hashlib.sha256(password.encode()).digest()
            self.key = base64.urlsafe_b64encode(key)
            self.cipher = Fernet(self.key)
        else:
            self.cipher = None
    
    def conectar(self):
        """Conecta a la base encriptada solo en memoria"""
        if not self.cipher:
            print("❌ No se proporcionó contraseña")
            return False
        
        try:
            # Verificar que existe el archivo encriptado
            import os
            if not os.path.exists(self.archivo_encriptado):
                print(f"❌ No se encuentra {self.archivo_encriptado}")
                return False
            
            # Leer y desencriptar
            with open(self.archivo_encriptado, 'rb') as f:
                datos_encriptados = f.read()
            
            # Desencriptar datos
            self.datos_en_memoria = self.cipher.decrypt(datos_encriptados)
            
            # Conectar a la base en memoria usando los datos desencriptados
            self.conn = sqlite3.connect(":memory:")
            
            # Restaurar la base de datos en memoria
            self.conn.executescript(self._bytes_to_sql())
            
            print("✅ Conectado a la base encriptada (solo en memoria)")
            return True
            
        except Exception as e:
            print(f"❌ Error al conectar: {e}")
            return False
    
    def _bytes_to_sql(self):
        """Convierte los bytes de la base a SQL ejecutable"""
        try:
            # Crear una conexión temporal para extraer el SQL
            temp_conn = sqlite3.connect(":memory:")
            temp_conn.execute("CREATE TABLE temp_restore (data BLOB)")
            temp_conn.execute("INSERT INTO temp_restore VALUES (?)", (self.datos_en_memoria,))
            
            # Usar el método de SQLite para restaurar
            temp_conn.close()
            
            # Método alternativo: escribir a StringIO y leer como SQL
            import tempfile
            import os
            
            # Crear archivo temporal muy breve
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(self.datos_en_memoria)
                temp_path = temp_file.name
            
            try:
                # Conectar al archivo temporal y extraer estructura + datos
                temp_conn = sqlite3.connect(temp_path)
                
                # Obtener todas las sentencias de creación
                cursor = temp_conn.cursor()
                cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL")
                create_statements = cursor.fetchall()
                
                # Construir script SQL completo
                sql_script = ""
                
                # Agregar sentencias CREATE
                for stmt in create_statements:
                    sql_script += stmt[0] + ";\n"
                
                # Obtener datos de todas las tablas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    if table_name != 'sqlite_sequence':
                        cursor.execute(f"SELECT * FROM {table_name}")
                        rows = cursor.fetchall()
                        
                        if rows:
                            # Obtener info de columnas
                            cursor.execute(f"PRAGMA table_info({table_name})")
                            columns = cursor.fetchall()
                            placeholders = ','.join(['?' for _ in columns])
                            
                            for row in rows:
                                # Convertir valores a string SQL
                                values = []
                                for val in row:
                                    if val is None:
                                        values.append('NULL')
                                    elif isinstance(val, str):
                                        values.append(f"'{val.replace(chr(39), chr(39)+chr(39))}'")
                                    else:
                                        values.append(str(val))
                                
                                sql_script += f"INSERT INTO {table_name} VALUES ({','.join(values)});\n"
                
                temp_conn.close()
                return sql_script
                
            finally:
                # Eliminar archivo temporal
                os.unlink(temp_path)
                
        except Exception as e:
            print(f"❌ Error al procesar datos: {e}")
            return ""
    
    def guardar_cambios(self):
        """Guarda los cambios de vuelta al archivo encriptado"""
        if not self.conn or not self.cipher:
            print("❌ No hay conexión activa")
            return False
        
        try:
            # Crear archivo temporal en memoria para obtener los datos actualizados
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Hacer backup de la base en memoria a archivo temporal
                backup_conn = sqlite3.connect(temp_path)
                self.conn.backup(backup_conn)
                backup_conn.close()
                
                # Leer los datos actualizados
                with open(temp_path, 'rb') as f:
                    datos_actualizados = f.read()
                
                # Encriptar y guardar
                datos_encriptados = self.cipher.encrypt(datos_actualizados)
                
                with open(self.archivo_encriptado, 'wb') as f:
                    f.write(datos_encriptados)
                
                print("💾 Cambios guardados y encriptados")
                return True
                
            finally:
                # Eliminar archivo temporal
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            print(f"❌ Error al guardar: {e}")
            return False
    
    def desconectar(self):
        """Cierra la conexión y limpia memoria"""
        if self.conn:
            self.conn.close()
            self.conn = None
        
        self.datos_en_memoria = None
        print("🔒 Conexión cerrada y datos eliminados de memoria")
    
    def ejecutar_consulta(self, query, params=None):
        """Ejecuta una consulta SELECT"""
        if not self.conn:
            print("❌ No hay conexión activa")
            return []
        
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        except Exception as e:
            print(f"❌ Error en consulta: {e}")
            return []
    
    def insertar(self, tabla, datos):
        """Inserta datos en una tabla"""
        if not self.conn:
            print("❌ No hay conexión activa")
            return False
        
        try:
            placeholders = ','.join(['?' for _ in datos])
            query = f"INSERT INTO {tabla} VALUES ({placeholders})"
            cursor = self.conn.cursor()
            cursor.execute(query, datos)
            print(f"✅ Registro insertado en {tabla}")
            return True
        except Exception as e:
            print(f"❌ Error al insertar: {e}")
            return False
    
    def actualizar(self, query, params=None):
        """Ejecuta una consulta UPDATE"""
        if not self.conn:
            print("❌ No hay conexión activa")
            return False
        
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            print(f"✅ Actualización completada. Filas afectadas: {cursor.rowcount}")
            return True
        except Exception as e:
            print(f"❌ Error al actualizar: {e}")
            return False
    
    def listar_tablas(self):
        """Lista todas las tablas"""
        if not self.conn:
            print("❌ No hay conexión activa")
            return []
        
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tablas = cursor.fetchall()
            return [tabla[0] for tabla in tablas]
        except Exception as e:
            print(f"❌ Error al listar tablas: {e}")
            return []

# Ejemplo de uso
if __name__ == "__main__":
    import getpass
    
    password = "MiPasswordSeguro123"
    
    # Crear manager
    db = MontraManager(password=password)
    
    # Conectar
    if db.conectar():
        # Listar tablas
        tablas = db.listar_tablas()
        print(f"📋 Tablas disponibles: {tablas}")
        
        # Ejemplo de consulta
        if tablas:
            primera_tabla = tablas[0]
            print(f"\n🔍 Consultando tabla '{primera_tabla}':")
            resultados = db.ejecutar_consulta(f"SELECT * FROM {primera_tabla} LIMIT 5")
            
            for i, row in enumerate(resultados, 1):
                print(f"   {i}. {row}")
        
        # Cerrar (sin archivos temporales)
        db.desconectar()
    else:
        print("❌ No se pudo conectar")