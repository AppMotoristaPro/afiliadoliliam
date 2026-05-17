from flask import redirect, url_for
from app import create_app

app = create_app()

# Mapeia o link cru da raiz para abrir a tela de login automaticamente
@app.route('/')
def index():
    return redirect(url_for('admin.login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

