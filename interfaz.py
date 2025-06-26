import tkinter as tk
from tkinter import filedialog, messagebox
from procesador import procesar_kml

def seleccionar_archivo():
    archivo = filedialog.askopenfilename(
        title="Selecciona un archivo KML",
        filetypes=[("Archivos KML", "*.kml")]
    )
    if archivo:
        try:
            procesar_kml(archivo)
            messagebox.showinfo("Éxito", "Procesamiento completado.")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error:\n{e}")

root = tk.Tk()
root.title("Procesador de KML")

frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

label = tk.Label(frame, text="Selecciona un archivo KML para procesar:")
label.pack(pady=10)

btn = tk.Button(frame, text="Seleccionar archivo KML", command=seleccionar_archivo)
btn.pack(pady=10)

root.mainloop()