import os
import sys
import unittest
import django

def run_tests():
    # Añade el proyecto al path.
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
        
    # Configura Django antes de importar.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    
    # Importar la clase de pruebas del módulo test_sistema
    from pruebas_sistema_funcionales.test_sistema import PruebasSistemaFuncionales
    
    # Crear suite de pruebas
    suite = unittest.TestLoader().loadTestsFromTestCase(PruebasSistemaFuncionales)
    
    # Ejecutar las pruebas
    print("======================================================================")
    print("EJECUTANDO CASOS DE PRUEBA FUNCIONALES DEL SISTEMA (UT-10-01 a UT-15-02)")
    print("======================================================================")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Mostrar resumen
    print("\n======================================================================")
    print(f"Pruebas ejecutadas: {result.testsRun}")
    print(f"Pruebas exitosas: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Fallos (Failures): {len(result.failures)}")
    print(f"Errores (Errors): {len(result.errors)}")
    print("======================================================================")
    
    # Devuelve 1 si hay fallos.
    if not result.wasSuccessful():
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
