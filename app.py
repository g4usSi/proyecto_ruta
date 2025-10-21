from flask import Flask, render_template, request, jsonify
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from io import BytesIO
import base64
import os
import warnings
warnings.filterwarnings('ignore')
from grafo import Grafo
from automata_formal import Automata
from flask import send_file
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


app = Flask(__name__, static_folder='output', static_url_path='/output')

if not os.path.exists('output'):
    os.makedirs('output')

grafo_global = None
ruta_actual = None  # Guardar la ruta actual
distancia_actual = None  # Guardar la distancia actual

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
    
    grafo_global.agregar_arista(origen, destino, peso)
    
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
    global grafo_global
    
    grafo_global = Grafo(dirigido=False)
    
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
    global grafo_global, ruta_actual, distancia_actual
    
    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400
    
    datos = request.json
    origen = datos.get('origen', '').strip().upper()
    destino = datos.get('destino', '').strip().upper()
    
    if not origen or not destino:
        return jsonify({'exito': False, 'error': 'Origen y destino requeridos'}), 400
    
    distancia, ruta = grafo_global.dijkstra(origen, destino)
    
    if not ruta:
        return jsonify({
            'exito': False,
            'error': f'No hay ruta entre {origen} y {destino}'
        }), 404
    
    # Guardar la ruta y distancia actual
    ruta_actual = ruta
    distancia_actual = distancia
    
    automata = Automata(grafo_global, origen, destino)
    validacion = automata.procesar_cadena(ruta)
    
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
    global grafo_global, ruta_actual, distancia_actual

    if grafo_global is None or len(grafo_global.obtener_nodos()) == 0:
        return jsonify({'exito': False, 'error': 'No hay grafo para descargar'}), 400

    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)

    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)

    # Crear la visualización (con ruta si existe)
    if ruta_actual:
        fig, img_buffer = crear_figura_con_ruta(G, pos)
    else:
        fig, img_buffer = crear_figura_simple(G, pos)

    if formato.lower() == 'png':
        output_path = 'output/grafo.png'
        fig.savefig(output_path, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        return send_file(output_path, as_attachment=True, download_name='grafo.png', mimetype='image/png')

    elif formato.lower() == 'pdf':
        # Generar PDF con imagen y información de ruta
        pdf_path = 'output/grafo.pdf'
        c = canvas.Canvas(pdf_path, pagesize=letter)
        
        # Agregar imagen
        fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
        plt.close(fig)
        img_buffer.seek(0)
        
        c.drawImage(img_buffer, 50, 350, width=500, height=350)
        
        # Agregar información de ruta si existe
        if ruta_actual and distancia_actual is not None:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, 320, "Información de Ruta:")
            
            c.setFont("Helvetica", 11)
            # Formato: A -> B -> C -> ...
            ruta_texto = " → ".join(ruta_actual)
            c.drawString(50, 300, f"Ruta: {ruta_texto}")
            c.drawString(50, 280, f"Costo Total: {distancia_actual}")
        
        c.showPage()
        c.save()
        return send_file(pdf_path, as_attachment=True, download_name='grafo.pdf', mimetype='application/pdf')

    else:
        return jsonify({'exito': False, 'error': 'Formato no válido (usa png o pdf)'}), 400

def crear_figura_simple(G, pos):
    """Crea una figura simple del grafo"""
    fig = plt.figure(figsize=(10, 8))
    
    nx.draw(
        G, pos,
        with_labels=True,
        node_color='lightblue',
        node_size=1500,
        font_weight='bold',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_edges(
        G, pos,
        width=2,
        edge_color='gray',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo Actual', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    buffer = BytesIO()
    return fig, buffer

def crear_figura_con_ruta(G, pos):
    """Crea una figura del grafo con la ruta destacada"""
    fig = plt.figure(figsize=(10, 8))
    
    nodos_normales = [n for n in G.nodes() if n not in ruta_actual]
    nx.draw_networkx_nodes(G, pos, nodelist=nodos_normales, 
                          node_color='lightblue', node_size=1500)
    
    nx.draw_networkx_nodes(G, pos, nodelist=ruta_actual, 
                          node_color='lightcoral', node_size=1500)
    
    aristas_ruta = [(ruta_actual[i], ruta_actual[i+1]) 
                    for i in range(len(ruta_actual)-1)]
    aristas_normales = [(u, v) for u, v in G.edges() 
                        if (u, v) not in aristas_ruta and (v, u) not in aristas_ruta]
    
    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_normales,
        width=1, edge_color='gray',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )

    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_ruta,
        width=3, edge_color='red',
        arrows=grafo_global.dirigido,
        arrowsize=25,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo con Ruta Mas Corta Destacada', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    buffer = BytesIO()
    return fig, buffer

def generar_visualizacion_simple():
    global grafo_global
    
    if grafo_global is None or len(grafo_global.obtener_nodos()) == 0:
        return None
    
    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()
    
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)
    
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)
    
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    nx.draw(
        G, pos,
        with_labels=True,
        node_color='lightblue',
        node_size=1500,
        font_weight='bold',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_edges(
        G, pos,
        width=2,
        edge_color='gray',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo Actual', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return imagen_base64

def generar_visualizacion(ruta_destacada):
    global grafo_global
    
    G = nx.Graph() if not grafo_global.dirigido else nx.DiGraph()
    
    for nodo in grafo_global.obtener_nodos():
        G.add_node(nodo)
    
    for origen, destino, peso in grafo_global.obtener_aristas():
        G.add_edge(origen, destino, weight=peso)
    
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    nodos_normales = [n for n in G.nodes() if n not in ruta_destacada]
    nx.draw_networkx_nodes(G, pos, nodelist=nodos_normales, 
                          node_color='lightblue', node_size=1500)
    
    nx.draw_networkx_nodes(G, pos, nodelist=ruta_destacada, 
                          node_color='lightcoral', node_size=1500)
    
    aristas_ruta = [(ruta_destacada[i], ruta_destacada[i+1]) 
                    for i in range(len(ruta_destacada)-1)]
    aristas_normales = [(u, v) for u, v in G.edges() 
                        if (u, v) not in aristas_ruta and (v, u) not in aristas_ruta]
    
    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_normales,
        width=1, edge_color='gray',
        arrows=grafo_global.dirigido,
        arrowsize=20,
        connectionstyle="arc3,rad=0.05"
    )

    nx.draw_networkx_edges(
        G, pos,
        edgelist=aristas_ruta,
        width=3, edge_color='red',
        arrows=grafo_global.dirigido,
        arrowsize=25,
        connectionstyle="arc3,rad=0.05"
    )
    
    nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold')
    
    edge_labels = {(u, v): w for u, v, w in grafo_global.obtener_aristas()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=10)
    
    plt.title('Grafo con Ruta Más Corta Destacada', fontsize=16, fontweight='bold')
    plt.axis('off')
    plt.tight_layout()
    
    buffer = BytesIO()
    plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
    buffer.seek(0)
    imagen_base64 = base64.b64encode(buffer.read()).decode()
    plt.close()
    
    return imagen_base64

@app.route('/obtener_grafo', methods=['GET'])
def obtener_grafo():
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
    global grafo_global
    
    if grafo_global is None:
        return jsonify({'exito': False, 'error': 'Grafo no inicializado'}), 400
    
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