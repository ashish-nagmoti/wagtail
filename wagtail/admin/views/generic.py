from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import BaseCreateView, BaseDeleteView, BaseUpdateView
from django.views.generic.list import BaseListView

from wagtail.admin import messages
from wagtail.core import hooks


class PermissionCheckedMixin:
    """
    Mixin for class-based views to enforce permission checks according to
    a permission policy (see wagtail.core.permission_policies).

    To take advantage of this, subclasses should set the class property:
    * permission_policy (a policy object)
    and either of:
    * permission_required (an action name such as 'add', 'change' or 'delete')
    * any_permission_required (a list of action names - the user must have
      one or more of those permissions)
    """
    permission_policy = None
    permission_required = None
    any_permission_required = None

    def dispatch(self, request, *args, **kwargs):
        if self.permission_policy is not None:

            if self.permission_required is not None:
                if not self.permission_policy.user_has_permission(
                    request.user, self.permission_required
                ):
                    raise PermissionDenied

            if self.any_permission_required is not None:
                if not self.permission_policy.user_has_any_permission(
                    request.user, self.any_permission_required
                ):
                    raise PermissionDenied

        return super().dispatch(request, *args, **kwargs)


class HookResponseMixin:
    """
    A mixin for class-based views to support hooks like `before_edit_page`, which are triggered
    during execution of some operation and can return a response to halt that operation.
    """

    def run_hook(self, hook_name, *args, **kwargs):
        """
        Run the named hook, passing args and kwargs to each function registered under that hook name.
        If any return an HttpResponse, stop processing and return that response
        """
        for fn in hooks.get_hooks(hook_name):
            result = fn(*args, **kwargs)
            if hasattr(result, 'status_code'):
                return result


class IndexView(PermissionCheckedMixin, TemplateResponseMixin, BaseListView):
    model = None
    header_icon = ''
    index_url_name = None
    add_url_name = None
    edit_url_name = None
    context_object_name = None
    any_permission_required = ['add', 'change', 'delete']
    template_name = None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_add'] = (
            self.permission_policy is None
            or self.permission_policy.user_has_permission(self.request.user, 'add')
        )
        return context


class CreateView(PermissionCheckedMixin, TemplateResponseMixin, BaseCreateView):
    model = None
    form_class = None
    header_icon = ''
    index_url_name = None
    add_url_name = None
    edit_url_name = None
    template_name = 'wagtailadmin/generic/create.html'
    permission_required = 'add'
    success_message = None
    error_message = None

    def get_add_url(self):
        return reverse(self.add_url_name)

    def get_success_url(self):
        return reverse(self.index_url_name)

    def get_success_message(self, instance):
        if self.success_message is None:
            return None
        return self.success_message.format(instance)

    def get_error_message(self):
        if self.error_message is None:
            return None
        return self.error_message

    def save_instance(self):
        """
        Called after the form is successfully validated - saves the object to the db
        and returns the new object. Override this to implement custom save logic.
        """
        return self.form.save()

    def form_valid(self, form):
        self.form = form
        self.object = self.save_instance()
        success_message = self.get_success_message(self.object)
        if success_message is not None:
            messages.success(self.request, success_message, buttons=[
                messages.button(reverse(self.edit_url_name, args=(self.object.id,)), _('Edit'))
            ])
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        self.form = form
        error_message = self.get_error_message()
        if error_message is not None:
            messages.error(self.request, error_message)
        return super().form_invalid(form)


class EditView(PermissionCheckedMixin, TemplateResponseMixin, BaseUpdateView):
    model = None
    form_class = None
    header_icon = ''
    index_url_name = None
    edit_url_name = None
    delete_url_name = None
    page_title = gettext_lazy("Editing")
    context_object_name = None
    template_name = 'wagtailadmin/generic/edit.html'
    permission_required = 'change'
    delete_item_label = gettext_lazy("Delete")
    success_message = None
    error_message = None

    def get_object(self, queryset=None):
        if 'pk' not in self.kwargs:
            self.kwargs['pk'] = self.args[0]
        return super().get_object(queryset)

    def get_page_subtitle(self):
        return str(self.object)

    def get_edit_url(self):
        return reverse(self.edit_url_name, args=(self.object.id,))

    def get_delete_url(self):
        return reverse(self.delete_url_name, args=(self.object.id,))

    def get_success_url(self):
        return reverse(self.index_url_name)

    def save_instance(self):
        """
        Called after the form is successfully validated - saves the object to the db.
        Override this to implement custom save logic.
        """
        return self.form.save()

    def get_success_message(self):
        if self.success_message is None:
            return None
        return self.success_message.format(self.object)

    def get_error_message(self):
        if self.error_message is None:
            return None
        return self.error_message

    def form_valid(self, form):
        self.form = form
        self.object = self.save_instance()
        success_message = self.get_success_message()
        if success_message is not None:
            messages.success(self.request, success_message, buttons=[
                messages.button(reverse(self.edit_url_name, args=(self.object.id,)), _('Edit'))
            ])
        return redirect(self.get_success_url())

    def form_invalid(self, form):
        self.form = form
        error_message = self.get_error_message()
        if error_message is not None:
            messages.error(self.request, error_message)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['can_delete'] = (
            self.permission_policy is None
            or self.permission_policy.user_has_permission(self.request.user, 'delete')
        ),
        return context


class DeleteView(PermissionCheckedMixin, TemplateResponseMixin, BaseDeleteView):
    model = None
    header_icon = ''
    index_url_name = None
    delete_url_name = None
    template_name = 'wagtailadmin/generic/confirm_delete.html'
    context_object_name = None
    permission_required = 'delete'
    success_message = None

    def get_object(self, queryset=None):
        if 'pk' not in self.kwargs:
            self.kwargs['pk'] = self.args[0]
        return super().get_object(queryset)

    def get_success_url(self):
        return reverse(self.index_url_name)

    def get_page_subtitle(self):
        return str(self.object)

    def get_delete_url(self):
        return reverse(self.delete_url_name, args=(self.object.id,))

    def get_success_message(self):
        if self.success_message is None:
            return None
        return self.success_message.format(self.object)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, self.get_success_message())
        return response
