import heapq
from collections import defaultdict

class Grafo:
    
    def __init__(self, dirigido=False):
        self.adyacencia = defaultdict(list)
        self.nodos = set()
        self.dirigido = dirigido
    
    def agregar_nodo(self, nodo):
        self.nodos.add(nodo)
    
    def agregar_arista(self, origen, destino, peso=1):
        self.agregar_nodo(origen)
        self.agregar_nodo(destino)
        
        self.adyacencia[origen].append((destino, peso))
        
        if not self.dirigido:
            self.adyacencia[destino].append((origen, peso))
    
    def dijkstra(self, origen, destino):
        if origen not in self.nodos or destino not in self.nodos:
            return None, []
        
        # Inicializar distancias
        distancias = {nodo: float('inf') for nodo in self.nodos}
        distancias[origen] = 0
        
        # Rastrear el camino
        previos = {nodo: None for nodo in self.nodos}
        
        # Cola de prioridad: (distancia, nodo)
        cola = [(0, origen)]
        visitados = set()
        
        while cola:
            distancia_actual, nodo_actual = heapq.heappop(cola)
            
            if nodo_actual in visitados:
                continue
            
            visitados.add(nodo_actual)
            
            # Si llegamos al destino, terminar
            if nodo_actual == destino:
                break
            
            # Explorar vecinos
            for vecino, peso in self.adyacencia[nodo_actual]:
                if vecino not in visitados:
                    nueva_distancia = distancia_actual + peso
                    
                    if nueva_distancia < distancias[vecino]:
                        distancias[vecino] = nueva_distancia
                        previos[vecino] = nodo_actual
                        heapq.heappush(cola, (nueva_distancia, vecino))
        
        # Reconstruir la ruta
        ruta = []
        nodo = destino
        
        if distancias[destino] != float('inf'):
            while nodo is not None:
                ruta.append(nodo)
                nodo = previos[nodo]
            ruta.reverse()
        
        return distancias[destino], ruta
    
    def obtener_nodos(self):
        """Retorna la lista de nodos"""
        return list(self.nodos)
    
    def obtener_aristas(self):
        """Retorna la lista de aristas con formato [(origen, destino, peso), ...]"""
        aristas = []
        visitadas = set()
        
        for origen in self.adyacencia:
            for destino, peso in self.adyacencia[origen]:
                # Evitar duplicados en grafos no dirigidos
                if self.dirigido or (origen, destino) not in visitadas and (destino, origen) not in visitadas:
                    aristas.append((origen, destino, peso))
                    if not self.dirigido:
                        visitadas.add((origen, destino))
        
        return aristas