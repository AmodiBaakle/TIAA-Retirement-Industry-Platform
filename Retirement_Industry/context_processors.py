from django.conf import settings


def branding(request):
    """Expose the configurable app name to every template as {{ app_name }}."""
    return {'app_name': getattr(settings, 'APP_NAME', 'TARA')}


def user_shell(request):
    """Provide the logged-in user's name + gamification header (XP/level/streak)
    to every app-shell page, so base.html always has what it needs."""
    pid = request.session.get('pid')
    if not pid:
        return {}
    try:
        from Retirement_Industry.models import Profile_Info
        from Retirement_Industry import gamification
        person = Profile_Info.objects.filter(person_id=pid).first()
        if not person:
            return {}
        state = gamification.get_state(pid)
        return {
            'shell_user': {
                'name': person.name,
                'mail': person.mail,
                'initial': (person.name or 'U')[:1].upper(),
            },
            'shell_game': state,
        }
    except Exception:
        return {}
