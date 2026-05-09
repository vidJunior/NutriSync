from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django import forms
from django.shortcuts import redirect
from django.contrib import messages
from .models import RegistroComida, ItemRegistro, RegistroHabito, PerfilUsuario
from .forms import RegistroHabitoForm, PerfilForm
from .views import verificar_logros
from alimentos.models import Alimento


TW_INPUT = "w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-green-500"
TW_SELECT = "w-full border border-gray-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-green-500"


class RegistroListView(LoginRequiredMixin, ListView):
    model = RegistroComida
    template_name = "nutricion/lista_registros.html"
    context_object_name = "registros"

    def get_queryset(self):
        return RegistroComida.objects.filter(usuario=self.request.user)


class RegistroCreateView(LoginRequiredMixin, CreateView):
    model = RegistroComida
    template_name = "nutricion/form_comida.html"
    fields = ["fecha", "tipo_comida"]
    success_url = reverse_lazy("nutricion:lista_registros")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields["fecha"].widget = forms.DateInput(
            attrs={"type": "date", "class": TW_INPUT}
        )
        form.fields["tipo_comida"].widget.attrs["class"] = TW_SELECT
        form.fields["alimento"] = forms.ModelChoiceField(
            queryset=Alimento.objects.activos(),
            label="Alimento",
            widget=forms.Select(attrs={"class": TW_SELECT}),
        )
        form.fields["cantidad_g"] = forms.DecimalField(
            label="Cantidad (g)",
            widget=forms.NumberInput(attrs={"class": TW_INPUT}),
        )
        return form

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        self.object = form.save()
        ItemRegistro.objects.create(
            registro=self.object,
            alimento=form.cleaned_data["alimento"],
            cantidad_g=form.cleaned_data["cantidad_g"],
        )
        return redirect(self.get_success_url())


class HabitoCreateView(LoginRequiredMixin, CreateView):
    model = RegistroHabito
    form_class = RegistroHabitoForm
    template_name = "nutricion/form_habito.html"
    success_url = reverse_lazy("nutricion:lista_habitos")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name in form.fields:
            if isinstance(form.fields[field_name], forms.Select):
                form.fields[field_name].widget.attrs["class"] = TW_SELECT
            elif isinstance(form.fields[field_name], forms.DateInput):
                form.fields[field_name].widget.attrs["class"] = TW_INPUT
                form.fields[field_name].widget.attrs["type"] = "date"
            else:
                form.fields[field_name].widget.attrs["class"] = TW_INPUT
        return form

    def form_valid(self, form):
        obj, _ = RegistroHabito.objects.update_or_create(
            usuario=self.request.user,
            fecha=form.cleaned_data["fecha"],
            defaults={
                "vasos_agua": form.cleaned_data["vasos_agua"],
                "horas_sueno": form.cleaned_data["horas_sueno"],
                "pasos": form.cleaned_data["pasos"],
                "minutos_ejercicio": form.cleaned_data["minutos_ejercicio"],
                "tipo_ejercicio": form.cleaned_data["tipo_ejercicio"],
            },
        )
        self.object = obj
        nuevos = verificar_logros(self.request.user, fecha=form.cleaned_data["fecha"])
        if nuevos:
            messages.success(
                self.request,
                f"¡Nuevos logros desbloqueados: {', '.join(l.nombre for l in nuevos)}!",
            )
        return redirect(self.get_success_url())


class PerfilUpdateView(LoginRequiredMixin, UpdateView):
    model = PerfilUsuario
    form_class = PerfilForm
    template_name = "nutricion/perfil_form.html"
    success_url = reverse_lazy("nutricion:dashboard")

    def get_object(self, queryset=None):
        obj, created = PerfilUsuario.objects.get_or_create(usuario=self.request.user)
        return obj

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field_name in form.fields:
            if isinstance(form.fields[field_name], forms.Select):
                form.fields[field_name].widget.attrs["class"] = TW_SELECT
            else:
                form.fields[field_name].widget.attrs["class"] = TW_INPUT
        return form
