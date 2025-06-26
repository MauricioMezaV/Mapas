import tkinter as tk
from tkinter import filedialog, messagebox
from kml_processor import process_kml
from PIL import Image, ImageTk

def select_file():
    archivo = filedialog.askopenfilename(filetypes=[("KML files", "*.kml")])
    if archivo:
        try:
            process_kml(archivo)
            messagebox.showinfo("Éxito", "Archivo procesado correctamente.\nLos resultados están en la carpeta 'outputs'.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al procesar el archivo:\n{e}")

root = tk.Tk()
root.title("Procesador de KML")
root.geometry("720x450")
root.configure(bg="#0a1633")  # azul marino oscuro

# Cargar imagen del logo
try:
    imagen = Image.open("assets/logo.webp")
    imagen = imagen.resize((250, 180), Image.LANCZOS)
    imagen_tk = ImageTk.PhotoImage(imagen)
    label_imagen = tk.Label(root, image=imagen_tk, bg="#0a1633")
    label_imagen.image = imagen_tk
    label_imagen.pack(pady=20)
except Exception as e:
    print(f"No se pudo cargar la imagen: {e}")

# Instrucciones
instrucciones = tk.Label(
    root,
    text="Seleccione un archivo KML para procesar.",
    font=("Arial", 14, "bold"),
    fg="white",
    bg="#0a1633"
)
instrucciones.pack(pady=15)

# Botón para seleccionar archivo
btn = tk.Button(
    root,
    text="Seleccionar archivo KML",
    command=select_file,
    font=("Arial", 12, "bold"),
    fg="white",
    bg="#193366",
    activebackground="#254080",
    activeforeground="white"
)
btn.pack(pady=30)
