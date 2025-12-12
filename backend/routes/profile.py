from flask import Blueprint, render_template, redirect, url_for, session, flash
from backend.models import User, Progress, Lesson

profile_bp = Blueprint('profile', __name__, template_folder='../../frontend/templates')

@profile_bp.route('/')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        flash('Silakan login terlebih dahulu','warning')
        return redirect(url_for('auth.login'))
    user = User.query.get_or_404(user_id)
    progresses = Progress.query.filter_by(user_id=user_id).all()
    lessons_done = []
    for p in progresses:
        lesson = Lesson.query.get(p.lesson_id)
        lessons_done.append({'lesson': lesson, 'score': p.score, 'completed': p.completed})
    return render_template('profile.html', user=user, lessons=lessons_done)
