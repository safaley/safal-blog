
from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, CreateRegisterForm, CreateLoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#Login
login_manager = LoginManager()
login_manager.init_app(app)

##Gravatar
gravatar = Gravatar(
    app,
    size=100,
    rating='g',
    default='retro',
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None
)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

##Decorators


def admin_only(f):
    @wraps(f)
    def wrapper_function(*args, **kwargs):
        if current_user.get_id() != "1":
            return abort(403)
        return f(*args, **kwargs)
    return wrapper_function

##CONFIGURE TABLES


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(2000), nullable=False)
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    # author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, ForeignKey('users.id'))
    author = relationship("User", back_populates="comments")
    post_id = db.Column(db.Integer, ForeignKey('blog_posts.id'))
    parent_post = relationship("BlogPost", back_populates="comments")


db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = CreateRegisterForm()
    if request.method == "POST":
        email = form.email.data
        if User.query.filter_by(email=email).first():
            flash("Email already exists.Log in instead")
            return redirect(url_for('login'))
        password = form.password.data
        name = form.name.data
        new_user = User(
            email=email,
            password=generate_password_hash(password, salt_length=8),
            name=name
        )

        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = CreateLoginForm()
    if request.method == "POST":
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("Invalid email. Please try again.")
            return redirect(url_for('login'))
        elif check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        else:
            flash("Invalid Password. Please type correct password.")
            return redirect(url_for("login"))

    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if request.method == "POST":
        new_comment = Comment(
            text=request.form.get('ckeditor'),
            author_id=current_user.id,
            post_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=requested_post.id))

    all_comments = Comment.query.filter_by(post_id=requested_post.id).all()
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form, comments=all_comments)


@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)


@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)


@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if request.method == "POST":
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if request.method == "POST":
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        # post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
