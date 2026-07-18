import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile/services/api_service.dart';
import 'package:mobile/screens/login_screen.dart';

class PerfilDialog extends StatefulWidget {
  final Map<String, dynamic> perfil;
  final Function(Map<String, dynamic>) onProfileUpdated;

  const PerfilDialog({
    super.key,
    required this.perfil,
    required this.onProfileUpdated,
  });

  @override
  State<PerfilDialog> createState() => _PerfilDialogState();
}

class _PerfilDialogState extends State<PerfilDialog> {
  final _telefonoController = TextEditingController();
  final _picker = ImagePicker();

  String _editAvatarColor = '#10B981';
  String? _editFotoUrl;
  bool _actualizando = false;
  String? _perfilError;

  @override
  void initState() {
    super.initState();
    _telefonoController.text = widget.perfil['telefono'] ?? '';
    _editAvatarColor = widget.perfil['avatar_color'] ?? '#10B981';
    _editFotoUrl = widget.perfil['foto_url'] as String?;
  }

  @override
  void dispose() {
    _telefonoController.dispose();
    super.dispose();
  }

  // Abre el selector de imágenes.
  Future<void> _elegirFoto() async {
    try {
      final XFile? image = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: 300,
        maxHeight: 300,
        imageQuality: 70,
      );

      if (image != null) {
        final bytes = await image.readAsBytes();
        final base64String = base64Encode(bytes);
        setState(() {
          _editFotoUrl = 'data:image/jpeg;base64,$base64String';
        });
      }
    } catch (e) {
      setState(() {
        _perfilError = 'Error al abrir la galería o procesar la foto.';
      });
    }
  }

  Future<void> _guardarCambios() async {
    final tel = _telefonoController.text.trim();
    if (tel.isEmpty) {
      setState(() {
        _perfilError = 'El teléfono es obligatorio.';
      });
      return;
    }

    setState(() {
      _actualizando = true;
      _perfilError = null;
    });

    try {
      final res = await ApiService.updatePerfil(
        nombre: widget.perfil['nombre'] ?? '',
        apellido: widget.perfil['apellido'] ?? '',
        telefono: tel,
        email: widget.perfil['email'] ?? '',
        avatarColor: _editAvatarColor,
        fotoUrl: _editFotoUrl,
      );

      if (res['success'] == true || res['telefono'] != null) {
        final Map<String, dynamic> nuevosDatos = Map.from(widget.perfil);
        nuevosDatos['telefono'] = tel;
        nuevosDatos['avatar_color'] = _editAvatarColor;
        nuevosDatos['foto_url'] = _editFotoUrl;
        
        widget.onProfileUpdated(nuevosDatos);
        if (mounted) Navigator.of(context).pop();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _perfilError = e.toString().replaceAll('Exception:', '').trim();
          _actualizando = false;
        });
      }
    }
  }

  String _obtenerIniciales(String nombre, String apellido) {
    final n = nombre.trim();
    final a = apellido.trim();
    final iN = n.isNotEmpty ? n.substring(0, 1) : '';
    final iA = a.isNotEmpty ? a.substring(0, 1) : '';
    final res = iN + iA;
    return res.isNotEmpty ? res.toUpperCase() : 'P';
  }

  Color _parseColor(String colorHex, Color defaultColor) {
    try {
      final buffer = StringBuffer();
      if (colorHex.length == 6 || colorHex.length == 7) buffer.write('ff');
      buffer.write(colorHex.replaceFirst('#', ''));
      return Color(int.parse(buffer.toString(), radix: 16));
    } catch (e) {
      return defaultColor;
    }
  }

  Future<void> _handleLogout() async {
    await ApiService.cerrarSesion();
    if (mounted) {
      Navigator.of(context).pop(); // Cerrar el diálogo
      Navigator.of(context).pushAndRemoveUntil(
        MaterialPageRoute(builder: (_) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final dialogBg = isDark ? const Color(0xFF1C1D24) : Colors.white;
    final staticBoxBg = isDark ? const Color(0xFF262730) : const Color(0xFFF3F4F6);
    final textThemeColor = isDark ? Colors.white : const Color(0xFF1F2937);

    final nombrePaciente = widget.perfil['nombre'] ?? '';
    final apellidoPaciente = widget.perfil['apellido'] ?? '';
    final emailPaciente = widget.perfil['email'] ?? '';
    final dniPaciente = widget.perfil['dni'] ?? '';
    final currentAvatarColor = _parseColor(_editAvatarColor, const Color(0xFF10B981));

    return Dialog(
      backgroundColor: Colors.transparent,
      insetPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 24),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: dialogBg,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: isDark ? Colors.white.withValues(alpha: 0.06) : Colors.grey[200]!,
          ),
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Header del modal
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Editar Perfil',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: textThemeColor,
                    ),
                  ),
                  IconButton(
                    icon: Icon(Icons.close_rounded, color: isDark ? Colors.grey[400] : const Color(0xFF4B5563)),
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 12),

              if (_perfilError != null)
                Container(
                  padding: const EdgeInsets.all(10),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.redAccent.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.redAccent.withValues(alpha: 0.3)),
                  ),
                  child: Text(
                    _perfilError!,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.redAccent, fontSize: 12, fontWeight: FontWeight.w500),
                  ),
                ),

              // Selector de foto de perfil
              Center(
                child: Column(
                  children: [
                    GestureDetector(
                      onTap: _elegirFoto,
                      child: Stack(
                        children: [
                          if (_editFotoUrl != null && _editFotoUrl!.isNotEmpty)
                            ClipRRect(
                              borderRadius: BorderRadius.circular(40),
                              child: Image.memory(
                                base64Decode(_editFotoUrl!.replaceFirst(RegExp(r'data:image/[^;]+;base64,'), '')),
                                width: 80,
                                height: 80,
                                fit: BoxFit.cover,
                                errorBuilder: (context, error, stackTrace) => CircleAvatar(
                                  radius: 40,
                                  backgroundColor: currentAvatarColor,
                                  child: Text(
                                    _obtenerIniciales(nombrePaciente, apellidoPaciente),
                                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 26),
                                  ),
                                ),
                              ),
                            )
                          else
                            CircleAvatar(
                              radius: 40,
                              backgroundColor: currentAvatarColor,
                              child: Text(
                                _obtenerIniciales(nombrePaciente, apellidoPaciente),
                                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 26),
                              ),
                            ),
                          Positioned(
                            bottom: 0,
                            right: 0,
                            child: Container(
                              padding: const EdgeInsets.all(4),
                              decoration: const BoxDecoration(
                                color: Color(0xFF10B981),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.camera_alt_rounded,
                                size: 16,
                                color: Colors.white,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextButton(
                      onPressed: _elegirFoto,
                      child: const Text(
                        'Seleccionar Foto de Galería',
                        style: TextStyle(
                          color: Color(0xFF10B981),
                          fontWeight: FontWeight.bold,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Información de solo lectura
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: staticBoxBg,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  children: [
                    Text(
                      '$nombrePaciente $apellidoPaciente',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: textThemeColor,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '📧 $emailPaciente  —  🆔 DNI $dniPaciente',
                      style: TextStyle(
                        fontSize: 11,
                        color: isDark ? Colors.grey[400] : const Color(0xFF6B7280),
                      ),
                    ),
                  ],
                ),
              ),

              // Único campo editable: Teléfono
              const SizedBox(height: 16),
              const Text(
                'TELÉFONO DE CONTACTO',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF90949C),
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 6),
              TextField(
                controller: _telefonoController,
                keyboardType: TextInputType.phone,
                style: TextStyle(color: isDark ? Colors.white : Colors.black, fontSize: 14),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: staticBoxBg,
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide.none,
                  ),
                ),
              ),

              // Selector de color del avatar
              const SizedBox(height: 16),
              const Text(
                'COLOR DE FONDO DEL AVATAR',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF90949C),
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: ['#10B981', '#3B82F6', '#EF4444', '#8B5CF6', '#F59E0B'].map((cStr) {
                  final isSelected = _editAvatarColor == cStr;
                  final color = _parseColor(cStr, Colors.grey);
                  return GestureDetector(
                    onTap: () => setState(() => _editAvatarColor = cStr),
                    child: Container(
                      width: 32,
                      height: 32,
                      decoration: BoxDecoration(
                        color: color,
                        shape: BoxShape.circle,
                        border: isSelected
                            ? Border.all(color: Colors.white, width: 2.5)
                            : null,
                        boxShadow: isSelected
                            ? [const BoxShadow(color: Colors.black38, blurRadius: 4, offset: Offset(0, 2))]
                            : null,
                      ),
                    ),
                  );
                }).toList(),
              ),

              // Botón de Cerrar Sesión destacado
              const SizedBox(height: 24),
              GestureDetector(
                onTap: _handleLogout,
                child: Container(
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.redAccent.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.redAccent.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: const [
                      Icon(Icons.logout_rounded, color: Colors.redAccent, size: 18),
                      SizedBox(width: 8),
                      Text(
                        'Cerrar Sesión',
                        style: TextStyle(
                          color: Colors.redAccent,
                          fontWeight: FontWeight.bold,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              // Botones Guardar / Cancelar
              const SizedBox(height: 20),
              Row(
                children: [
                  Expanded(
                    child: SizedBox(
                      height: 44,
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        style: OutlinedButton.styleFrom(
                          side: BorderSide(color: isDark ? Colors.white24 : Colors.grey[300]!),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        child: Text(
                          'Cancelar',
                          style: TextStyle(color: textThemeColor, fontWeight: FontWeight.bold),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: SizedBox(
                      height: 44,
                      child: ElevatedButton(
                        onPressed: _actualizando ? null : _guardarCambios,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF10B981),
                          foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          elevation: 0,
                        ),
                        child: _actualizando
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                              )
                            : const Text('Guardar', style: TextStyle(fontWeight: FontWeight.bold)),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
