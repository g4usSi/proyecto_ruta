class Automata:
    def __init__(self, grafo, estado_inicial, estados_aceptacion):
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
                # Crear simbolo de transicion: "origen -> destino"
                simbolo = f"{origen}→{destino}"
                self.sigma.add(simbolo)
    
    def _construir_transiciones(self):
        self.delta = {}  # Funcion de transicion
        self.w = {}      # Función de pesos
        
        for origen in self.grafo.adyacencia:
            for destino, peso in self.grafo.adyacencia[origen]:
                # δ(estado, símbolo) = nuevo_estado
                simbolo = f"{origen}→{destino}"
                self.delta[(origen, simbolo)] = destino
                
                # w(transición) = peso
                self.w[simbolo] = peso
    
    def procesar_cadena(self, cadena_nodos):
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
        return {
            'Q': sorted(list(self.Q)),              # Estados
            'sigma': sorted(list(self.sigma)),      # Alfabeto
            'q0': self.q0,                          # Estado inicial
            'F': sorted(list(self.F)),              # Estados de aceptación
            'transiciones': len(self.delta),        # Número de transiciones
            'pesos': dict(sorted(self.w.items()))  # Función de pesos
        }