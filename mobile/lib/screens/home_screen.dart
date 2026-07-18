import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:mobile/screens/tabs/dashboard_tab.dart';
import 'package:mobile/screens/tabs/plan_tab.dart';
import 'package:mobile/screens/tabs/medidas_tab.dart';
import 'package:mobile/screens/tabs/indicaciones_tab.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;

  final List<Widget> _tabs = [
    const DashboardTab(),
    const PlanTab(),
    const MedidasTab(),
    const IndicacionesTab(),
  ];

  Widget _buildNavItem(int index, IconData activeIcon, IconData inactiveIcon, String label, Color activeColor, Color? inactiveColor) {
    final isSelected = _currentIndex == index;

    return Expanded(
      child: GestureDetector(
        onTap: () {
          Feedback.forTap(context);
          setState(() {
            _currentIndex = index;
          });
        },
        behavior: HitTestBehavior.opaque,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
          decoration: BoxDecoration(
            color: isSelected ? activeColor.withValues(alpha: 0.08) : Colors.transparent,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isSelected ? activeIcon : inactiveIcon,
                color: isSelected ? activeColor : inactiveColor,
                size: 22,
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.w800 : FontWeight.w600,
                  color: isSelected ? activeColor : inactiveColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final activeColor = const Color(0xFF10B981);
    final inactiveColor = isDark ? Colors.grey[400] : const Color(0xFF6B7280);

    return Scaffold(
      backgroundColor: isDark ? const Color(0xFF0B1220) : const Color(0xFFF5F9FF),
      body: SafeArea(
        child: Stack(
          fit: StackFit.expand,
          children: [
            Positioned(
              top: -120,
              left: -100,
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [const Color(0xFF10B981).withValues(alpha: 0.22), Colors.transparent],
                  ),
                ),
              ),
            ),
            Positioned(
              top: 60,
              right: -80,
              child: Container(
                width: 180,
                height: 180,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [const Color(0xFF3B82F6).withValues(alpha: 0.16), Colors.transparent],
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -90,
              right: -90,
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [const Color(0xFFF59E0B).withValues(alpha: 0.14), Colors.transparent],
                  ),
                ),
              ),
            ),
          // Pestaña activa
            Positioned.fill(
              bottom: 85, // Dar espacio para que la barra inferior no tape el contenido del scroll
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 200),
                child: KeyedSubtree(
                  key: ValueKey<int>(_currentIndex),
                  child: _tabs[_currentIndex],
                ),
              ),
            ),

            // Navegación inferior
            Positioned(
              left: 16,
              right: 16,
              bottom: 16,
              child: SafeArea(
                top: false,
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(24),
                  child: BackdropFilter(
                    filter: ImageFilter.blur(sigmaX: 18, sigmaY: 18),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1C1D24).withValues(alpha: 0.84) : Colors.white.withValues(alpha: 0.88),
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(
                          color: isDark ? Colors.white.withValues(alpha: 0.08) : Colors.grey[200]!,
                        ),
                      ),
                      child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildNavItem(
                        0,
                        Icons.grid_view_rounded,
                        Icons.grid_view_outlined,
                        'Dashboard',
                        activeColor,
                        inactiveColor,
                      ),
                      _buildNavItem(
                        1,
                        Icons.restaurant_rounded,
                        Icons.restaurant_outlined,
                        'Alimentos',
                        activeColor,
                        inactiveColor,
                      ),
                      _buildNavItem(
                        2,
                        Icons.trending_up_rounded,
                        Icons.trending_up_outlined,
                        'Progreso',
                        activeColor,
                        inactiveColor,
                      ),
                      _buildNavItem(
                        3,
                        Icons.assignment_turned_in_rounded,
                        Icons.assignment_turned_in_outlined,
                        'Notas',
                        activeColor,
                        inactiveColor,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
          ],
        ),
      ),
    );
  }
}
