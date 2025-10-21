from flask import Flask, render_template, request, jsonify
import matplotlib

matplotlib.use('Agg')  # Backend sin GUI para evitar warnings
import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
import base64
import os
import warnings

warnings.filterwarnings('ignore')  # Ignorar warnings menores
from grafo import Grafo
from automata_formal import Automata
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

app = Flask(__name__, static_folder='output', static_url_path='/output')

# Crear carpeta output si no existe
if not os.path.exists('output'):
    os.makedirs('output')

# Paleta de colores basada en el diseño
COLORES = {
    'fondo': '#f8f9fa',
    'primario': '#2c3e50',
    'secundario': '#3498db',
    'acento': '#e74c3c',
    'texto': '#2c3e50',
    'borde': '#bdc3c7',
    'exito': '#27ae60',
    'nodo_normal': '#3498db',
    'nodo_ruta': '#e74c3c',
    'arista_normal': '#95a5a6',
    'arista_ruta': '#e74c3c',
    'fondo_nodo': '#ecf0f1'
}

# Grafo global que se mantendrá en sesión
grafo_global = None


@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/iniciar_grafo', methods=['POST'])
def iniciar_grafo():
    global grafo_global

    datos = request.json
    dirigido = datos.get('dirigido', False)

    grafo_global = Grafo(dirigido=dirigido)

    return jsonify({
        'exito': True,
        'mensaje': f'Grafo {"dirigido" if dirigido else "no dirigido"} inicializado',
        'tipo': 'dirigido' if dirigido else 'no dirigido'
    })


@app.route('/agregar_arista', methods=['POST'])
def agregar_arista():
    global grafo_global

    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400

    datos = request.json
    origen = datos.get('origen', '').strip().upper()
    destino = datos.get('destino', '').strip().upper()
    peso = float(datos.get('peso', 1))

    if not origen or not destino:
        return jsonify({'exito': False, 'error': 'Origen y destino requeridos'}), 400

    if origen == destino:
        return jsonify({'exito': False, 'error': 'El origen y destino no pueden ser iguales'}), 400

    if peso <= 0:
        return jsonify({'exito': False, 'error': 'El peso debe ser mayor a 0'}), 400

    # Agregar arista
    grafo_global.agregar_arista(origen, destino, peso)

    # Generar visualización
    img_base64 = generar_visualizacion_simple()

    return jsonify({
        'exito': True,
        'mensaje': f'Arista agregada: {origen} → {destino} (peso: {peso})',
        'nodos': grafo_global.obtener_nodos(),
        'aristas': grafo_global.obtener_aristas(),
        'imagen': img_base64
    })


@app.route('/crear_grafo_ejemplo', methods=['POST'])
def crear_grafo_ejemplo():
    """
    Crea un grafo de ejemplo para demostración.
    Grafo: A -> B(4) -> D(2)
               -> C(2) -> D(3)
    """
    global grafo_global

    grafo_global = Grafo(dirigido=False)

    # Agregar aristas
    aristas = [
        ('A', 'B', 4),
        ('A', 'C', 2),
        ('B', 'D', 2),
        ('C', 'D', 3),
        ('C', 'E', 5),
        ('D', 'E', 1)
    ]

    for origen, destino, peso in aristas:
        grafo_global.agregar_arista(origen, destino, peso)

    # Generar visualización
    img_base64 = generar_visualizacion_simple()

    return jsonify({
        'exito': True,
        'mensaje': 'Grafo de ejemplo creado',
        'nodos': grafo_global.obtener_nodos(),
        'aristas': grafo_global.obtener_aristas(),
        'imagen': img_base64
    })


@app.route('/calcular_ruta', methods=['POST'])
def calcular_ruta():
    """Calcula la ruta más corta entre dos nodos"""
    global grafo_global

    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400

    datos = request.json
    origen = datos.get('origen', '').strip().upper()
    destino = datos.get('destino', '').strip().upper()

    if not origen or not destino:
        return jsonify({'exito': False, 'error': 'Origen y destino requeridos'}), 400

    # Calcular ruta usando Dijkstra
    distancia, ruta = grafo_global.dijkstra(origen, destino)

    if not ruta:
        return jsonify({
            'exito': False,
            'error': f'No hay ruta entre {origen} y {destino}'
        }), 404

    # Crear autómata para validar formalmente la ruta
    automata = Automata(grafo_global, origen, destino)
    validacion = automata.procesar_cadena(ruta)

    # Generar visualización con ruta destacada
    img_base64 = generar_visualizacion(ruta)

    return jsonify({
        'exito': True,
        'distancia': distancia,
        'ruta': ruta,
        'validacion_formal': validacion,
        'imagen': img_base64,
        'descripcion_automata': automata.obtener_descripcion_formal()
    })


@app.route('/descargar_grafo/<formato>', methods=['GET'])
def descargar_grafo(formato):
    global grafo_global

    if grafo_global is None or len(grafo_global.obtener_nodos()) == 0:
        return jsonify({'exito': False, 'error': 'No hay grafo para descargar'}), 400

    # Crear grafo con NetworkX
    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    plt.figure(figsize=(10, 8), facecolor=COLORES['fondo'])
    nx.draw(G, pos, with_labels=True,
            node_color=COLORES['nodo_normal'],
            node_size=1500,
            font_weight='bold',
            font_color='white',
            edge_color=COLORES['arista_normal'])
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.axis('off')

    # Guardar temporalmente
    if formato.lower() == 'png':
        output_path = 'output/grafo.png'
        plt.savefig(output_path, format='png', dpi=100, bbox_inches='tight',
                    facecolor=COLORES['fondo'])
        plt.close()
        return send_file(output_path, as_attachment=True, download_name='grafo.png', mimetype='image/png')

    elif formato.lower() == 'pdf':
        # Generar PNG temporal
        buffer_img = BytesIO()
        plt.savefig(buffer_img, format='png', dpi=100, bbox_inches='tight',
                    facecolor=COLORES['fondo'])
        plt.close()
        buffer_img.seek(0)

        # Crear PDF y añadir la imagen
        pdf_path = 'output/grafo.pdf'
        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawImage(buffer_img, 50, 200, width=500, height=400)
        c.showPage()
        c.save()
        return send_file(pdf_path, as_attachment=True, download_name='grafo.pdf', mimetype='application/pdf')

    else:
        return jsonify({'exito': False, 'error': 'Formato no válido (usa png o pdf)'}), 400


def generar_visualizacion_simple():
    """Genera visualización básica del grafo actual sin ruta destacada"""
    global grafo_global

    if grafo_global is None or len(grafo_global.obtener_nodos()) == 0:
        return None

    # Crear grafo NetworkX
    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()

    # Agregar nodos
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)

    # Agregar aristas
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)

    # Crear figura con fondo de la paleta
    plt.figure(figsize=(10, 8), facecolor=COLORES['fondo'])
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Dibujar nodos
    nx.draw(
        G, pos,
        with_labels=True,
        node_color=COLORES['nodo_normal'],
        node_size=1500,
        font_weight='bold',
        font_color='white',
        edge_color=COLORES['arista_normal'],
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )

    # Dibujar aristas
    nx.draw_networkx_edges(
        G,
        pos,
        width=2,
        edge_color=COLORES['arista_normal'],
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )

    # Dibujar etiquetas
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', font_color='white')

    # Dibujar pesos
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)

    plt.title('Grafo Actual', fontsize=16, fontweight='bold', color=COLORES['texto'])
    plt.axis('off')
    plt.tight_layout()

    # Convertir a base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor=COLORES['fondo'])
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    return imagen_base64


def generar_visualizacion(ruta_destacada):
    """Genera visualización del grafo con la ruta destacada"""
    global grafo_global

    # Crear grafo NetworkX
    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()

    # Agregar nodos
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)

    # Agregar aristas
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)

    # Crear figura con fondo de la paleta
    plt.figure(figsize=(10, 8), facecolor=COLORES['fondo'])
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Dibujar nodos normales
    nodos_normales = [n for n in G.nodes() if n not in ruta_destacada]
    nx.draw_networkx_nodes(G, pos, nodelist=nodos_normales,
                           node_color=COLORES['nodo_normal'], node_size=1500)

    # Dibujar nodos de la ruta
    nx.draw_networkx_nodes(G, pos, nodelist=ruta_destacada,
                           node_color=COLORES['nodo_ruta'], node_size=1500)

    # Dibujar aristas normales
    aristas_ruta = [(ruta_destacada[i], ruta_destacada[i + 1])
                    for i in range(len(ruta_destacada) - 1)]
    aristas_normales = [(u, v) for u, v in G.edges() if (u, v) not in aristas_ruta and (v, u) not in aristas_ruta]

    # Dibujar aristas normales
    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_normales,
        width=1,
        edge_color=COLORES['arista_normal'],
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )

    # Dibujar aristas de la ruta con color de acento
    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_ruta,
        width=3,
        edge_color=COLORES['arista_ruta'],
        arrows=grafo_global.dirigido,
        arrowsize=25,
        connectionstyle="arc3,rad=0.05"
    )

    # Dibujar etiquetas de nodos
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', font_color='white')

    # Dibujar pesos
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)

    plt.title('Grafo con Ruta Más Corta Destacada', fontsize=16, fontweight='bold', color=COLORES['texto'])
    plt.axis('off')
    plt.tight_layout()

    # Convertir a base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight', facecolor=COLORES['fondo'])
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()

    return imagen_base64


@app.route('/obtener_grafo', methods=['GET'])
def obtener_grafo():
    """Retorna la información actual del grafo"""
    global grafo_global

    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400

    return jsonify({
        'exito': True,
        'nodos': grafo_global.obtener_nodos(),
        'aristas': grafo_global.obtener_aristas()
    })


@app.route('/info_automata', methods=['GET'])
def info_automata():
    """Retorna la información formal del autómata"""
    global grafo_global

    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400

    # Usar el primer y último nodo como ejemplo
    nodos = grafo_global.obtener_nodos()
    if len(nodos) < 2:
        return jsonify({'exito': False, 'error': 'Se necesitan al menos 2 nodos'}), 400

    automata = Automata(grafo_global, nodos[0], nodos[-1])

    return jsonify({
        'exito': True,
        'descripcion': automata.obtener_descripcion_formal()
    })


if __name__ == '__main__':
    app.run(debug=True)