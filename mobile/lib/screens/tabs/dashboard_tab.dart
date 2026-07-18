import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:mobile/services/api_service.dart';
import 'package:mobile/screens/perfil_dialog.dart';
import 'package:mobile/screens/archivos_screen.dart';
import 'package:mobile/screens/login_screen.dart';

class DashboardTab extends StatefulWidget {
  const DashboardTab({super.key});

  @override
  State<DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<DashboardTab> {
  bool _loading = false;
  Map<String, dynamic>? _perfil;
  Map<String, dynamic>? _plan;
  List<dynamic> _citas = [];
  String? _errorMsg;

  Future<void> _cerrarSesion() async {
    await ApiService.cerrarSesion();
    if (mounted) {
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  @override
  void initState() {
    super.initState();
    _cargarDatos();
  }

  Future<void> _cargarDatos() async {
    setState(() {
      _loading = true;
      _errorMsg = null;
    });

    try {
      final perfilData = await ApiService.getPerfil();
      
      Map<String, dynamic>? planData;
      try {
        planData = await ApiService.getPlanActivo();
      } catch (e) {
      // Omite un plan inexistente.
      }
      
      List<dynamic> citasData = [];
      try {
        citasData = await ApiService.getCitas();
      } catch (e) {
      // Omite fallos de citas.
      }



      if (mounted) {
        setState(() {
          _perfil = perfilData;
          _plan = planData;
          _citas = citasData;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMsg = 'Error al conectar al servidor de Django. Cargando datos locales.';
          _cargarDatosMock();
          _loading = false;
        });
      }
    }
  }

  void _cargarDatosMock() {
    _perfil = {
      'nombre': ApiService.nombrePaciente ?? 'Paciente',
      'apellido': 'Demo',
      'dni': '12345678',
      'edad': 28,
      'peso': 72.5,
      'talla': 175.0,
      'imc_inicial': 23.7,
      'imc_clasificacion': 'Normal',
      'email': ApiService.email ?? 'paciente.demo@nutrisync.com',
      'telefono': '987654321',
      'avatar_color': '#10B981',
      'foto_url': '',
    };
    _plan = {
      'nombre': 'Plan de Definición Basal',
      'tipo_plan': 'Definición Muscular',
      'calorias': 2200,
      'proteinas': 160,
      'carbohidratos': 210,
      'grasas': 65,
      'fibra': 28,
      'agua_recomendada': 2.8,
    };
    _citas = [
      {
        'fecha_hora': '2026-07-15 10:30',
        'tipo': 'Control de Rutina',
        'estado': 'Programada',
        'motivo': 'Evaluación del primer mes y reajuste de carbohidratos.',
        'nombre_nutricionista': 'Lic. Manuel Estévez',
      }
    ];
  }

  String _obtenerIniciales(String nombre, String apellido) {
    final n = nombre.trim();
    final a = apellido.trim();
    final iN = n.isNotEmpty ? n.substring(0, 1) : '';
    final iA = a.isNotEmpty ? a.substring(0, 1) : '';
    final res = iN + iA;
    return res.isNotEmpty ? res.toUpperCase() : 'P';
  }

  Color _parseColor(String? colorHex, Color defaultColor) {
    if (colorHex == null || colorHex.isEmpty) return defaultColor;
    try {
      final buffer = StringBuffer();
      if (colorHex.length == 6 || colorHex.length == 7) buffer.write('ff');
      buffer.write(colorHex.replaceFirst('#', ''));
      return Color(int.parse(buffer.toString(), radix: 16));
    } catch (e) {
      return defaultColor;
    }
  }

  void _abrirPerfilDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => PerfilDialog(
        perfil: _perfil!,
        onProfileUpdated: (Map<String, dynamic> nuevosDatos) {
          setState(() {
            _perfil = nuevosDatos;
          });
        },
      ),
    );
  }

  Widget _buildMacroCard(String label, int value, String unit, Color macroColor, double maxVal, isDark) {
    final double pct = (value / maxVal).clamp(0.0, 1.0);
    
    return Expanded(
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: isDark
                ? const [Color(0xFF111827), Color(0xFF1F2937)]
                : const [Color(0xFFFFFFFF), Color(0xFFEEF2FF)],
          ),
          borderRadius: BorderRadius.circular(18),
          border: Border.all(
            color: isDark ? Colors.white.withValues(alpha: 0.05) : Colors.grey[200]!,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: isDark ? 0.12 : 0.04),
              blurRadius: 12,
              offset: const Offset(0, 6),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label.toUpperCase(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                letterSpacing: 0.5,
                color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              '$value$unit',
              style: TextStyle(
                fontSize: 15,
                fontWeight: FontWeight.w900,
                color: macroColor,
              ),
            ),
            const SizedBox(height: 10),
                  // Progreso animado
            TweenAnimationBuilder<double>(
              tween: Tween<double>(begin: 0.0, end: pct),
              duration: const Duration(milliseconds: 1200),
              curve: Curves.easeOutBack,
              builder: (context, animVal, child) {
                return Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: isDark ? Colors.white12 : Colors.grey[200],
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        flex: (animVal * 100).toInt(),
                        child: Container(
                          decoration: BoxDecoration(
                            color: macroColor,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                      ),
                      Expanded(
                        flex: ((1 - animVal) * 100).toInt(),
                        child: Container(),
                      ),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final textThemeColor = isDark ? Colors.white : const Color(0xFF1F2937);
    final cardColor = isDark ? const Color(0xFF1C1D24) : Colors.white;

    if (_loading && _perfil == null) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFF10B981)),
      );
    }

    final nombrePaciente = _perfil?['nombre'] ?? ApiService.nombrePaciente ?? 'Paciente';
    final avatarColorStr = _perfil?['avatar_color'] ?? '#10B981';
    final avatarColor = _parseColor(avatarColorStr, const Color(0xFF10B981));
    final fotoUrl = _perfil?['foto_url'] as String?;

    return RefreshIndicator(
      onRefresh: _cargarDatos,
      color: const Color(0xFF10B981),
      child: TweenAnimationBuilder<double>(
        tween: Tween<double>(begin: 0.0, end: 1.0),
        duration: const Duration(milliseconds: 900),
        curve: Curves.easeOut,
        builder: (context, value, child) {
          return Opacity(
            opacity: value,
            child: Transform.translate(
              offset: Offset(0, 20 * (1 - value)),
              child: child,
            ),
          );
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16.0),
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header Superior
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                GestureDetector(
                  onTap: _abrirPerfilDialog,
                  behavior: HitTestBehavior.opaque,
                  child: Row(
                    children: [
                      // Avatar circular
                      if (fotoUrl != null && fotoUrl.isNotEmpty)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(21),
                          child: Image.memory(
                            base64Decode(fotoUrl.replaceFirst(RegExp(r'data:image/[^;]+;base64,'), '')),
                            width: 42,
                            height: 42,
                            fit: BoxFit.cover,
                             errorBuilder: (context, error, stackTrace) => CircleAvatar(
                              radius: 21,
                              backgroundColor: avatarColor,
                              child: Text(
                                _obtenerIniciales(nombrePaciente, _perfil?['apellido'] ?? ''),
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                              ),
                            ),
                          ),
                        )
                      else
                        CircleAvatar(
                          radius: 21,
                          backgroundColor: avatarColor,
                          child: Text(
                            _obtenerIniciales(nombrePaciente, _perfil?['apellido'] ?? ''),
                            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
                          ),
                        ),
                      const SizedBox(width: 12),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Bienvenido,',
                            style: TextStyle(
                              fontSize: 12,
                              color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          Text(
                            nombrePaciente,
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: textThemeColor,
                              letterSpacing: -0.5,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                // Botones de Acción (Documentos y Perfil)
                Row(
                  children: [
                    IconButton(
                      icon: Icon(Icons.folder_shared_outlined, color: isDark ? Colors.grey[450] : const Color(0xFF4B5563)),
                      onPressed: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(builder: (context) => const ArchivosScreen()),
                        );
                      },
                    ),
                    IconButton(
                      icon: Icon(Icons.settings_outlined, color: isDark ? Colors.grey[450] : const Color(0xFF4B5563)),
                      onPressed: _abrirPerfilDialog,
                    ),
                    IconButton(
                      icon: const Icon(Icons.logout, color: Colors.redAccent),
                      onPressed: _cerrarSesion,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 20),

            if (_errorMsg != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.amber.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.amber.withValues(alpha: 0.3)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline_rounded, color: Colors.amber, size: 18),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        _errorMsg!,
                        style: const TextStyle(color: Colors.amber, fontSize: 11, fontWeight: FontWeight.w500),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
            ],

            // Tarjeta de Calorías Principal
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: isDark ? Colors.white.withValues(alpha: 0.04) : Colors.grey[200]!,
                ),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: isDark ? 0.15 : 0.03),
                    blurRadius: 10,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  Text(
                    'Objetivo Diario de Energía',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                    ),
                  ),
                  const SizedBox(height: 10),
                // Resumen de calorías
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.baseline,
                    textBaseline: TextBaseline.alphabetic,
                    children: [
                      Text(
                        '${_plan?['calorias'] ?? 2000}',
                        style: const TextStyle(
                          fontSize: 42,
                          fontWeight: FontWeight.w900,
                          color: Color(0xFF10B981),
                          letterSpacing: -1.0,
                        ),
                      ),
                      const SizedBox(width: 4),
                      const Text(
                        'kcal',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF10B981),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    '🎯 ${_plan?['nombre'] ?? 'Plan Activo'}',
                    style: const TextStyle(
                      color: Color(0xFF10B981),
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Fila de Macros Animados
            Row(
              children: [
                _buildMacroCard('Proteínas', _plan?['proteinas'] ?? 140, 'g', Colors.redAccent, 160, isDark),
                const SizedBox(width: 12),
                _buildMacroCard('Carbohidratos', _plan?['carbohidratos'] ?? 200, 'g', const Color(0xFF3B82F6), 250, isDark),
                const SizedBox(width: 12),
                _buildMacroCard('Grasas', _plan?['grasas'] ?? 65, 'g', const Color(0xFFF59E0B), 80, isDark),
              ],
            ),
            const SizedBox(height: 16),

            // Próxima Cita
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isDark ? Colors.white.withValues(alpha: 0.04) : Colors.grey[200]!,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '📅 Próxima Consulta',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 12),
                  if (_citas.isNotEmpty) ...[
                    Text(
                      _citas[0]['fecha_hora'] ?? '',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Tipo: ${_citas[0]['tipo']} — Profesional: ${_citas[0]['nombre_nutricionista']}',
                      style: TextStyle(
                        fontSize: 12,
                        color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Motivo: ${_citas[0]['motivo']}',
                      style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic),
                    ),
                  ] else
                    Text(
                      'No tienes consultas programadas para esta semana.',
                      style: TextStyle(
                        color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                        fontStyle: FontStyle.italic,
                        fontSize: 13,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Estado Actual (IMC)
            Container(
              padding: const EdgeInsets.all(16),
              width: double.infinity,
              decoration: BoxDecoration(
                color: cardColor,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: isDark ? Colors.white.withValues(alpha: 0.04) : Colors.grey[200]!,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    '⚖️ Estado Clínico de Referencia',
                    style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Peso de Entrada',
                            style: TextStyle(
                              fontSize: 10,
                              color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${_perfil?['peso'] ?? 70.0} kg',
                            style: TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.white : Colors.black,
                            ),
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'IMC Inicial',
                            style: TextStyle(
                              fontSize: 10,
                              color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${_perfil?['imc_inicial'] ?? 22.5}',
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF10B981),
                            ),
                          ),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Clasificación',
                            style: TextStyle(
                              fontSize: 10,
                              color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${_perfil?['imc_clasificacion'] ?? 'Normal'}',
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                              color: isDark ? Colors.grey[300] : const Color(0xFF4B5563),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
    );
  }
}
