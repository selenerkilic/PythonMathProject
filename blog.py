from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps

app=Flask(__name__)

app.secret_key = "mathblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "" 
app.config["MYSQL_DB"] = "mathblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız.")
            return redirect(url_for("login"))
    return decorated_function

class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min=5, max=35)])
    username = StringField("Kullanıcı Adı",validators=[validators.length(min=5)])
    email = StringField("Mail Adresi", validators= [validators.Email(message="Lütfen geçerli bir mail adresi giriniz!")])
    password = PasswordField("Parola", validators=[validators.DataRequired(message= "Lütfen parolanızı belirleyiniz."),
    validators.EqualTo(fieldname="confirm", message="Parolanız uyuşmuyor.")])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

class ArticleForm(Form):
    title = StringField("Makale Başlığı", validators=[validators.length(min=3 , max=50)])
    content = TextAreaField("Makale İçeriği", validators=[validators.DataRequired(message="Bu alan boş geçilmez"),
    validators.length(min=10)])

#KAYIT OLUŞTURMA
@app.route("/register", methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users (name,username,email,password) VALUES (%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,username,email,password))

        mysql.connection.commit()

        cursor.close()

        flash("Kaydınız başarıyla gerçekleştirildi.","success")

        return redirect(url_for("login"))
    else:

        return render_template("register.html", form = form )


#LOGIN İŞLEMİ
@app.route("/login",methods = ["GET","POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = ("Select * from users where username = %s")

        result = cursor.execute(sorgu,(username,))

        if result>0:
            data = cursor.fetchone()
            real_password = data["password"] 

            if sha256_crypt.verify(password_entered,real_password):
               flash("Başarıyla giriş yaptınız.","success")
               
               session["logged_in"] = True
               session["username"] = username 


               return redirect(url_for("dashboard"))
            else:
                flash("Parolanızı yanlış girdiniz.","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunamadı...","danger")        
            return redirect(url_for("login"))

    return render_template("login.html", form = form)


#Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

#Kontrol Paneli

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    
    sorgu = "Select * from articles where author = %s"

    result = cursor.execute(sorgu,(session["username"],))

    if result>0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")



    
@app.route("/addarticle",methods=["GET","POST"])
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor() 

        sorgu = "Insert into articles (title,author,content) VALUES(%s,%s,%s)"

        cursor.execute(sorgu,(title,session["username"],content))

        mysql.connection.commit()

        cursor.close()

        flash("Makaleniz başarıyla kaydedildi.","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form = form)


#Makale Sayfası
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result = cursor.execute(sorgu)

    if result>0:
        articles = cursor.fetchall()

        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

@app.route("/")
def index():
    return render_template("index.html")

#Detay Sayfası
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where id = %s"

    result = cursor.execute(sorgu,(id,))

    if result>0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

#Makale Silme 
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()

    sorgu = "Select * from articles where author = %s and id= %s"

    result = cursor.execute(sorgu,(session["username"],id))

    if result>0:
        sorgu2 = "Delete from articles where id = %s"
        cursor.execute(sorgu2,(id,))
        mysql.connection.commit()

        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok!! ","danger")
        return redirect(url_for("index"))

#Makale Güncelleme
@app.route("/edit/<string:id>",methods = ["GET","POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()

        sorgu = "Select * From articles where id = %s and author = %s"

        result = cursor.execute(sorgu,(id,session["username"]))

        if result == 0:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.","danger")
            return redirect(url_for("index"))

        else: 
            article = cursor.fetchone()
            form = ArticleForm() #şu anki makaleni içeriği ile oluşturacağın için request.form demedik

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html", form = form) 

    else:
       #post request
       form = ArticleForm(request.form)

       newTitle = form.title.data
       newContent = form.content.data 

       sorgu2 = "Update articles Set title = %s, content=%s where id = %s "

       cursor = mysql.connection.cursor()

       cursor.execute(sorgu2,(newTitle,newContent,id))

       mysql.connection.commit()

       flash("Makale başarıyla güncellendi.","success")

       return redirect(url_for("dashboard"))

#Arama - Search
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method=="GET":
        return redirect(url_for("index"))
    else:
        keyword= request.form.get("keyword")

        cursor = mysql.connection.cursor()

        sorgu = "Select * From articles where title like '%"+keyword+"%'"

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı..","warning")
            return redirect(url_for("articles"))

        else:
            articles = cursor.fetchall()

            return render_template("articles.html", articles = articles)

if __name__ == '__main__':
    app.run(debug=True)