class Automata:
    """
    Clase que modela formalmente el sistema de búsqueda de rutas como un autómata.
    
    Elementos del autómata (A = (Q, Σ, δ, q₀, F, w)):
    - Q: Conjunto de estados (nodos del grafo)
    - Σ: Alfabeto (etiquetas de transiciones/aristas)
    - δ: Función de transición (adyacencia del grafo)
    - q₀: Estado inicial (nodo origen)
    - F: Estados de aceptación (nodo destino)
    - w: Función de pesos (costos de transiciones)
    """
    
    def __init__(self, grafo, estado_inicial, estados_aceptacion):
        """
        Inicializa el autómata basado en un grafo.
        
        Args:
            grafo: Objeto Grafo
            estado_inicial: Nodo origen (q₀)
            estados_aceptacion: Lista de nodos destino (F)
        """
        self.grafo = grafo
        self.Q = set(grafo.obtener_nodos())  # Estados
        self.q0 = estado_inicial              # Estado inicial
        self.F = set(estados_aceptacion) if isinstance(estados_aceptacion, list) else {estados_aceptacion}
        
        # Construir alfabeto y transiciones
        self._construir_alfabeto()
        self._construir_transiciones()
    
    def _construir_alfabeto(self):
        """Construye el alfabeto Σ a partir de las aristas del grafo"""
        self.sigma = set()
        
        for origen in self.grafo.adyacencia:
            for destino, peso in self.grafo.adyacencia[origen]:
                # Crear símbolo de transición: "origen->destino"
                simbolo = f"{origen}→{destino}"
                self.sigma.add(simbolo)
    
    def _construir_transiciones(self):
        """Construye la función de transición δ y pesos w"""
        self.delta = {}  # Función de transición
        self.w = {}      # Función de pesos
        
        for origen in self.grafo.adyacencia:
            for destino, peso in self.grafo.adyacencia[origen]:
                # δ(estado, símbolo) = nuevo_estado
                simbolo = f"{origen}→{destino}"
                self.delta[(origen, simbolo)] = destino
                
                # w(transición) = peso
                self.w[simbolo] = peso
    
    def procesar_cadena(self, cadena_nodos):
        """
        Verifica si una cadena (secuencia de nodos) es aceptada por el autómata.
        
        Args:
            cadena_nodos: Lista de nodos [n1, n2, n3, ...]
        
        Returns:
            dict: {
                'aceptada': bool,
                'estado_actual': nodo actual o None,
                'paso_fallo': índice donde falló (None si se acepta),
                'costo_total': suma de pesos de transiciones
            }
        """
        if len(cadena_nodos) < 2:
            return {
                'aceptada': False,
                'estado_actual': None,
                'paso_fallo': 0,
                'costo_total': 0
            }
        
        estado_actual = cadena_nodos[0]
        costo_total = 0
        
        # Verificar que comienza en estado inicial
        if estado_actual != self.q0:
            return {
                'aceptada': False,
                'estado_actual': estado_actual,
                'paso_fallo': 0,
                'costo_total': 0
            }
        
        # Procesar la cadena paso a paso
        for i in range(len(cadena_nodos) - 1):
            origen = cadena_nodos[i]
            destino = cadena_nodos[i + 1]
            simbolo = f"{origen}→{destino}"
            
            # Verificar si la transición existe
            if (origen, simbolo) not in self.delta:
                return {
                    'aceptada': False,
                    'estado_actual': origen,
                    'paso_fallo': i + 1,
                    'costo_total': costo_total
                }
            
            # Ejecutar transición
            estado_actual = self.delta[(origen, simbolo)]
            costo_total += self.w[simbolo]
        
        # Verificar si terminamos en un estado de aceptación
        aceptada = estado_actual in self.F
        
        return {
            'aceptada': aceptada,
            'estado_actual': estado_actual,
            'paso_fallo': None if aceptada else len(cadena_nodos),
            'costo_total': costo_total
        }
    
    def obtener_descripcion_formal(self):
        """Retorna la descripción formal del autómata"""
        return {
            'Q': sorted(list(self.Q)),              # Estados
            'sigma': sorted(list(self.sigma)),      # Alfabeto
            'q0': self.q0,                          # Estado inicial
            'F': sorted(list(self.F)),              # Estados de aceptación
            'transiciones': len(self.delta),        # Número de transiciones
            'pesos': dict(sorted(self.w.items()))  # Función de pesos
        }