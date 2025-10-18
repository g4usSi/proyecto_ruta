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

app = Flask(__name__, static_folder='output', static_url_path='/output')

# Crear carpeta output si no existe
if not os.path.exists('output'):
    os.makedirs('output')

# Grafo global que se mantendrá en sesión
grafo_global = None

@app.route('/')
def inicio():
    """Ruta principal - muestra el formulario"""
    return render_template('index.html')

@app.route('/iniciar_grafo', methods=['POST'])
def iniciar_grafo():
    """Inicializa un nuevo grafo vacío"""
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
    """Agrega una arista al grafo y retorna visualización actualizada"""
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
    
    # Crear figura
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Dibujar nodos
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=1500)
    
    # Dibujar aristas
    nx.draw_networkx_edges(G, pos, width=2, edge_color='gray')
    
    # Dibujar etiquetas
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Dibujar pesos
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo Actual', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # Convertir a base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
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
    
    # Crear figura
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Dibujar nodos normales
    nodos_normales = [n for n in G.nodes() if n not in ruta_destacada]
    nx.draw_networkx_nodes(G, pos, nodelist=nodos_normales, 
                          node_color='lightblue', node_size=1500)
    
    # Dibujar nodos de la ruta
    nx.draw_networkx_nodes(G, pos, nodelist=ruta_destacada, 
                          node_color='lightcoral', node_size=1500)
    
    # Dibujar aristas normales
    aristas_ruta = [(ruta_destacada[i], ruta_destacada[i+1]) 
                    for i in range(len(ruta_destacada)-1)]
    aristas_normales = [(u, v) for u, v in G.edges() if (u, v) not in aristas_ruta and (v, u) not in aristas_ruta]
    
    nx.draw_networkx_edges(G, pos, edgelist=aristas_normales, 
                          width=1, edge_color='gray')
    nx.draw_networkx_edges(G, pos, edgelist=aristas_ruta, 
                          width=3, edge_color='red')
    
    # Dibujar etiquetas
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    # Dibujar pesos
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo con Ruta Más Corta Destacada', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    # Convertir a base64
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
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