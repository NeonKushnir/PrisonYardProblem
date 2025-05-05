import matplotlib.pyplot as plt
import random
from math import floor
import tkinter as tk
from tkinter import filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import Counter
import os
from scipy.spatial import Delaunay

canvas_widget = None

# Зчитування координат точок з файлу
def read_points_from_file(filename='points.txt'):
    with open(filename, 'r') as file:
        lines = file.readlines()
    return [tuple(map(int, line.strip().split(', '))) for line in lines]

# Генерація випадкового ортогонального полігону з парною кількістю вершин
def create_random_orthogonal_polygon(num_points=20):
    points = []
    current_x = 0
    current_y = 0
    turned = False
    direction = 'vertical'
    num_points -= num_points % 2

    for _ in range(num_points - 1):
        points.append((current_x, current_y))

        if current_y >= num_points * 0.5:
            turned = True

        if direction == 'vertical':
            if not turned:
                current_y += random.randint(1, 4)
                direction = 'horizontal'
            else:
                current_y -= random.randint(1, 4)
                direction = 'horizontal'
        else:
            current_x += random.randint(1, 5)
            direction = 'vertical'

        if current_y <= 0:
            turned = not turned
            return create_random_orthogonal_polygon(num_points)

    points.append((current_x, 0))

    filename = 'random_points.txt'
    with open(filename, 'w') as file:
        for point in points:
            file.write(f"{point[0]}, {point[1]}\n")

# Перевірка, чи видно точку test_pos з точки cam_pos
# Видимість тільки по горизонталі або вертикалі, без перетину з ребрами полігону
def is_visible(polygon, cam_pos, test_pos):
    if cam_pos == test_pos:
        return True
    x1, y1 = cam_pos
    x2, y2 = test_pos
    if x1 != x2 and y1 != y2:
        return False
    for p1, p2 in zip(polygon, polygon[1:] + [polygon[0]]):
        if (cam_pos in [p1, p2]) or (test_pos in [p1, p2]):
            continue
        if x1 == x2 and p1[0] == p2[0] == x1:
            if min(p1[1], p2[1]) < max(y1, y2) and max(p1[1], p2[1]) > min(y1, y2):
                return False
        elif y1 == y2 and p1[1] == p2[1] == y1:
            if min(p1[0], p2[0]) < max(x1, x2) and max(p1[0], p2[0]) > min(x1, x2):
                return False
    return True

# Геометрична евристика для розміщення камер: вибір точки з найбільшою видимістю
def place_cameras_geometry(points):
    n = len(points)
    uncovered = set(range(n))
    cameras = []

    while uncovered:
        best_score = -1
        best_point = None
        best_visible = set()
        for i in uncovered:
            visible = set(j for j in uncovered if is_visible(points, points[i], points[j]))
            if len(visible) > best_score:
                best_score = len(visible)
                best_visible = visible
                best_point = i
        if best_point is None:
            break
        cameras.append(points[best_point])
        uncovered -= best_visible

    print(f"[GEOMETRIC HEURISTIC] Cameras placed: {len(cameras)}")
    return cameras

# Жадібний підхід до розміщення камер
def place_cameras_greedy(points):
    n = len(points)
    uncovered = set(range(n))
    cameras = []
    visibility_map = []
    for i in range(n):
        visible_from_i = set()
        for j in range(n):
            if is_visible(points, points[i], points[j]):
                visible_from_i.add(j)
        visibility_map.append(visible_from_i)
    used = set()
    visibility_score = Counter({i: len(v) for i, v in enumerate(visibility_map)})
    while uncovered:
        best_index = -1
        best_score = -1
        for idx in range(n):
            if idx in used:
                continue
            score = len(visibility_map[idx] & uncovered) + 0.01 * visibility_score[idx]
            if score > best_score:
                best_score = score
                best_index = idx
        if best_index == -1:
            break
        cameras.append(points[best_index])
        uncovered -= visibility_map[best_index]
        used.add(best_index)
    print(f"[GREEDY] Cameras placed: {len(cameras)} (⌊n/4⌋={floor(n/4)}, ⌊n/5⌋={floor(n/5)})")
    return cameras

# Розміщення камер на основі тріангуляції Делоне
def place_cameras_delaunay(points):
    tri = Delaunay(points)
    triangles = tri.simplices.tolist()
    triangle_points = [[points[idx] for idx in triangle] for triangle in triangles]
    cameras = []
    remaining = triangle_points[:]
    while remaining:
        all_pts = [pt for tri in remaining for pt in tri]
        count = Counter(all_pts)
        best, _ = count.most_common(1)[0]
        cameras.append(best)
        remaining = [tri for tri in remaining if best not in tri]
    print(f"[DELAUNAY] Cameras placed: {len(cameras)}")
    return cameras

# Візуалізація результатів усіх трьох методів
def draw_comparison(points):
    global canvas_widget
    if canvas_widget:
        canvas_widget.get_tk_widget().destroy()

    fig = Figure(figsize=(15, 5), dpi=100)
    axs = [fig.add_subplot(131), fig.add_subplot(132), fig.add_subplot(133)]

    methods = [
        (place_cameras_greedy, 'Greedy'),
        (place_cameras_delaunay, 'Delaunay'),
        (place_cameras_geometry, 'Geometric')
    ]

    x = [p[0] for p in points] + [points[0][0]]
    y = [p[1] for p in points] + [points[0][1]]

    for ax, (method, title) in zip(axs, methods):
        cameras = method(points)
        ax.plot(x, y, 'r-', label='Polygon')
        ax.scatter([p[0] for p in points], [p[1] for p in points], c='blue', label='Vertices')
        ax.scatter([p[0] for p in cameras], [p[1] for p in cameras], c='black', label='Cameras', s=60)
        ax.set_title(f"{title}: {len(cameras)} cameras")
        ax.grid(True)
        ax.legend(loc='upper right')

    canvas_widget = FigureCanvasTkAgg(fig, master=output_frame)
    canvas_widget.draw()
    canvas_widget.get_tk_widget().pack(pady=10)

# Обробка натискання кнопки "Analyze All Algorithms"
def analyze_all():
    mode = mode_var.get()
    if mode == '1':
        filename = "points.txt"
    elif mode == '2':
        count = int(entry_points.get())
        create_random_orthogonal_polygon(count)
        filename = "random_points.txt"
    else:
        return
    points = read_points_from_file(filename)
    draw_comparison(points)

# Завантаження текстового файлу з точками
def upload_file():
    file_path = filedialog.askopenfilename()
    if file_path:
        try:
            with open(file_path, 'r') as src, open('points.txt', 'w') as dst:
                dst.write(src.read())
            status_label.config(text="File uploaded successfully.")
        except Exception as e:
            status_label.config(text=f"Error: {e}")
    else:
        status_label.config(text="No file selected.")

# Графічний інтерфейс користувача (GUI) на основі Tkinter
window = tk.Tk()
window.title("Prison Yard Camera Placement")
window.geometry("1200x720")
window.configure(bg="#f0f0f0")

mode_var = tk.StringVar(value='1')

frame = tk.Frame(window, bg="#ffffff", bd=2, relief="groove")
frame.pack(padx=15, pady=15, fill="x")

label = tk.Label(frame, text="Input Mode:", font=("Segoe UI", 10, "bold"), bg="#ffffff")
label.pack(pady=(10, 0))

modes = [
    ("From File", '1'),
    ("Generate Random Polygon", '2')
]

for text, mode in modes:
    tk.Radiobutton(frame, text=text, variable=mode_var, value=mode, bg="#ffffff").pack(anchor='w', padx=10)

entry_label = tk.Label(frame, text="Number of Vertices:", bg="#ffffff")
entry_label.pack(pady=(10, 0))

entry_points = tk.Entry(frame)
entry_points.pack(pady=5, padx=10, fill="x")
entry_points.insert(0, "20")

tk.Button(frame, text="Upload .txt file", command=upload_file, bg="#e0e0e0").pack(pady=5, padx=10, fill="x")
status_label = tk.Label(frame, text="", bg="#ffffff", fg="green")
status_label.pack(pady=5)

tk.Button(frame, text="Analyze All Algorithms", command=analyze_all, bg="#d0ffd0").pack(pady=(5, 15), padx=10, fill="x")

output_frame = tk.Frame(window, bg="#f8f8f8", bd=1, relief="sunken")
output_frame.pack(padx=10, pady=10, fill="both", expand=True)

window.mainloop()
