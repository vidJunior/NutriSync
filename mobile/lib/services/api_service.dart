import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // URL del emulador Android.
  // Ejemplo:
  // flutter run -d <device> --dart-define=API_BASE_URL=http://192.168.101.18:8000/api/paciente
  static final String baseUrl = const String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  ).isNotEmpty
      ? const String.fromEnvironment('API_BASE_URL')
      : _defaultLocalUrl();

  static String _defaultLocalUrl() {
    // Apunta al servidor Django corriendo localmente en la máquina anfitriona desde el emulador de Android
    return 'http://10.0.2.2:8000/api/paciente';
  }

  static String? _token;
  static String? _nombrePaciente;
  static String? _email;

  // Carga el token guardado.
  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('token');
    _nombrePaciente = prefs.getString('nombre_paciente');
    _email = prefs.getString('email');
  }

  static bool get isAuthenticated => _token != null;
  static String? get token => _token;
  static String? get nombrePaciente => _nombrePaciente;
  static String? get email => _email;

  // Guarda la sesión.
  static Future<void> guardarSesion(String tokenValue, String nombreValue, String emailValue) async {
    _token = tokenValue;
    _nombrePaciente = nombreValue;
    _email = emailValue;

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', tokenValue);
    await prefs.setString('nombre_paciente', nombreValue);
    await prefs.setString('email', emailValue);
  }

  // Cierra la sesión.
  static Future<void> cerrarSesion() async {
    _token = null;
    _nombrePaciente = null;
    _email = null;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('nombre_paciente');
    await prefs.remove('email');
  }

  // Añade el token Bearer.
  static Map<String, String> _getHeaders() {
    final Map<String, String> headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_token != null) {
      headers['Authorization'] = 'Bearer $_token';
    }
    return headers;
  }

  // Inicio de sesión
  static Future<Map<String, dynamic>> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (response.statusCode == 200) {
        final tokenVal = decoded['token'] as String;
        final nombreVal = decoded['nombre_paciente'] as String;
        final emailVal = decoded['email'] as String;
        await guardarSesion(tokenVal, nombreVal, emailVal);
        return {'success': true};
      } else {
        return {'success': false, 'message': decoded['detail'] ?? 'Credenciales incorrectas.'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Ocurrió un error en la solicitud.'};
    }
  }

  // Registro vinculado
  static Future<Map<String, dynamic>> registrarVinculado({
    required String dni,
    required String codigoVinculacion,
    required String username,
    required String email,
    required String password,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/register-vinculado'),
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode({
          'dni': dni,
          'codigo_vinculacion': codigoVinculacion,
          'username': username,
          'email': email,
          'password': password,
        }),
      );

      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (response.statusCode == 200) {
        final tokenVal = decoded['token'] as String;
        final nombreVal = decoded['nombre_paciente'] as String;
        final emailVal = decoded['email'] as String;
        await guardarSesion(tokenVal, nombreVal, emailVal);
        return {'success': true};
      } else {
        return {'success': false, 'message': decoded['detail'] ?? 'El DNI o código ingresado no son válidos.'};
      }
    } catch (e) {
      return {'success': false, 'message': 'Ocurrió un error en la solicitud.'};
    }
  }

  // Perfil del paciente
  static Future<Map<String, dynamic>> getPerfil() async {
    final response = await http.get(
      Uri.parse('$baseUrl/perfil'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } else {
      throw Exception('Error al cargar perfil.');
    }
  }

  // Actualiza teléfono y avatar.
  static Future<Map<String, dynamic>> updatePerfil({
    required String nombre,
    required String apellido,
    required String telefono,
    required String email,
    String? avatarColor,
    String? fotoUrl,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/perfil/update'),
      headers: _getHeaders(),
      body: jsonEncode({
        'nombre': nombre,
        'apellido': apellido,
        'telefono': telefono,
        'email': email,
        'avatar_color': avatarColor,
        'foto_url': fotoUrl,
      }),
    );
    
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode == 200) {
      if (decoded['nombre_paciente'] != null) {
        _nombrePaciente = decoded['nombre_paciente'];
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('nombre_paciente', _nombrePaciente!);
      }
      return decoded as Map<String, dynamic>;
    } else {
      throw Exception(decoded['detail'] ?? 'Error al actualizar perfil.');
    }
  }

  // Plan alimentario activo
  static Future<Map<String, dynamic>> getPlanActivo() async {
    final response = await http.get(
      Uri.parse('$baseUrl/plan-activo'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
    } else {
      throw Exception('Error al cargar plan alimenticio.');
    }
  }

  // Historial de medidas
  static Future<List<dynamic>> getMedidas() async {
    final response = await http.get(
      Uri.parse('$baseUrl/medidas'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    } else {
      throw Exception('Error al cargar historial de medidas.');
    }
  }

  // Citas programadas
  static Future<List<dynamic>> getCitas() async {
    final response = await http.get(
      Uri.parse('$baseUrl/citas'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    } else {
      throw Exception('Error al cargar citas.');
    }
  }

  // Notas clínicas
  static Future<List<dynamic>> getNotas() async {
    final response = await http.get(
      Uri.parse('$baseUrl/notas'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    } else {
      throw Exception('Error al cargar notas clínicas.');
    }
  }

  // Recomendaciones
  static Future<List<dynamic>> getRecomendaciones() async {
    final response = await http.get(
      Uri.parse('$baseUrl/recomendaciones'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    } else {
      throw Exception('Error al cargar recomendaciones.');
    }
  }

  // Archivos del paciente
  static Future<List<dynamic>> getArchivos() async {
    final response = await http.get(
      Uri.parse('$baseUrl/archivos'),
      headers: _getHeaders(),
    );
    if (response.statusCode == 200) {
      return jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>;
    } else {
      throw Exception('Error al cargar archivos.');
    }
  }
}
