from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from sqlalchemy import text

db = SQLAlchemy()
login_manager = LoginManager()

# Minimal User model for Flask-Login
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    def get_id(self):
        return str(self.user_id)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    # Register Indian Rupee format filter
    @app.template_filter('inr')
    def format_inr_filter(value):
        try:
            value = float(value or 0)
        except (ValueError, TypeError):
            return value
        
        is_negative = value < 0
        value = abs(value)
        val_str = f"{value:.2f}"
        int_part, dec_part = val_str.split('.')
        
        if len(int_part) > 3:
            last_three = int_part[-3:]
            other_digits = int_part[:-3]
            groups = []
            while len(other_digits) > 0:
                groups.insert(0, other_digits[-2:])
                other_digits = other_digits[:-2]
            int_part = ",".join(groups) + "," + last_three
            
        formatted = f"{int_part}.{dec_part}"
        return "-" + formatted if is_negative else formatted

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            # Using raw SQL to demonstrate DBMS focus, though we could use ORM
            sql = text("SELECT user_id, username, password_hash FROM users WHERE username = :username")
            result = db.session.execute(sql, {'username': username}).fetchone()
            
            if result and check_password_hash(result.password_hash, password):
                user = db.session.get(User, result.user_id)
                login_user(user)
                return redirect(url_for('index')) # Will change to dashboard later
            else:
                flash('Invalid username or password', 'danger')
                
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('login'))
        
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        return redirect(url_for('login'))
        
    import click

    @app.cli.command("create-admin")
    @click.option('--username', prompt='Username', default='admin', help='Administrator username')
    @click.password_option(prompt='Password', confirmation_prompt=True, help='Administrator password')
    def create_admin(username, password):
        username = username.strip()
        if not username:
            click.echo("Error: Username cannot be blank.")
            return
        if not password:
            click.echo("Error: Password cannot be blank.")
            return
        
        hashed = generate_password_hash(password)
        sql = text("""
            INSERT INTO users (username, password_hash) 
            VALUES (:username, :password) 
            ON CONFLICT (username) 
            DO UPDATE SET password_hash = EXCLUDED.password_hash
        """)
        db.session.execute(sql, {'username': username, 'password': hashed})
        db.session.commit()
        click.echo(f"Admin user '{username}' configured successfully.")

    from routes.dashboard import dashboard_bp
    app.register_blueprint(dashboard_bp)
    
    from routes.projects import projects_bp
    app.register_blueprint(projects_bp)
    
    from routes.workers import workers_bp
    app.register_blueprint(workers_bp)
    
    from routes.tasks import tasks_bp
    app.register_blueprint(tasks_bp)

    from routes.equipment import equipment_bp
    app.register_blueprint(equipment_bp)
    
    from routes.materials import materials_bp
    app.register_blueprint(materials_bp)
    
    from routes.suppliers import suppliers_bp
    app.register_blueprint(suppliers_bp)
    
    from routes.purchases import purchases_bp
    app.register_blueprint(purchases_bp)
    
    from routes.financials import financials_bp
    app.register_blueprint(financials_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
