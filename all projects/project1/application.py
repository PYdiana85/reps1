import os
import requests
import json
from flask import Flask, session,render_template, request,jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker



app = Flask(__name__)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#-------------------------------------------------------------------------------------
## Home Page index.html
@app.route("/")
def index():
    return render_template('index.html')
#-------------------------------------------------------------------------------------
# the user registration page


@app.route("/registerUsers", methods=["POST"])
def registerUsers():
    name= request.form.get("name")
    password= request.form.get("pass")
    dob= request.form.get("dob")
    
    db.execute("Insert Into users(name,password,dob) values(:name,:password,:dob)",{"name":name,"password":password,"dob":dob})
    
    db.commit()
    return render_template('index.html',msg="Registerd Successfuly, Proceed to LOGIN")
#-------------------------------------------------------------------------------------

    #user login 


# the route that will take to books site after successful login
@app.route("/loginCheck", methods=["POST"])
def loginCheck():
    name= request.form.get("name")
    password= request.form.get("pass")
    user = db.execute("SELECT * FROM users WHERE name = :name and password = :password", {"name":name,"password":password}).fetchall()

    db.commit()
    
    
    if len(user) == 0:
        return render_template("index.html",msg_error="Please Enter Valid Login Credentials")
    else:
        x= user[0].id
        session["user_id"]= x
        session["name"] = user[0].name
        return render_template("booksSite.html")
    #----------- LOGOUT ------------
@app.route("/logout")
def logout():
    session.pop("user_id")
    session.pop("name")
    return render_template("index.html")

#-------------------------------------------------------------------------------------
#the book search page
@app.route("/booksSite")
def booksSite():
    return render_template("booksSite.html")
#-------------------------------------------------------------------------------------    
@app.route("/displayURBookS",methods=["POST"])
def displayURBookS():
    
    isbn = request.form.get("isbn")
    like_string_isbn = "%" + isbn + "%"
    bookname = request.form.get("bookname")
    like_string_title = "%" + bookname + "%"
    author_name = request.form.get("author_name")
    like_string_author = "%" + author_name + "%" 
    if isbn:
        book = db.execute("SELECT * FROM books WHERE isbn LIKE :like_string_isbn",{"like_string_isbn":like_string_isbn}).fetchall()
        return render_template("displayBooks.html",book=book)
    elif bookname:
        book = db.execute("SELECT * FROM books WHERE title LIKE :like_string_title",{"like_string_title":like_string_title}).fetchall()
        return render_template("displayBooks.html",book=book)
    elif author_name:
        book = db.execute("SELECT * FROM books WHERE author LIKE :like_string_author",{"like_string_author":like_string_author}).fetchall()
        return render_template("displayBooks.html",book=book)
    else:
        return render_template("booksSite.html",msg_error = "all fields are empty you need to specify your search criteria")
#-------------------------------------------------------------------------------------    

#view books details and reviews count from goodreads.com
@app.route("/addReview/<string:isbn>")
def addReview(isbn):
    book = db.execute("select * FROM books where isbn = :isbn",{"isbn":isbn}).fetchone()
    review = db.execute("select * FROM reviews where isbn = :isbn",{"isbn":isbn}).fetchall()
    
    res =requests.get("https://www.goodreads.com/book/review_counts.json",params={"key": "SpKTJPX39SYY6jb35N7A", "isbns":isbn.strip()})
    
    if res.status_code != 200:
        error = "ERROR: API request unsuccessful."
        return error
    
    else:
        error = ""
        data = res.json()
        outputs = data ["books"][0]
 
        averageRating =  str(outputs['average_rating'])  
        rating_counts =  str(outputs['work_ratings_count'])
        return render_template("addReview.html",book=book,review=review,averageRating=averageRating,rating_counts=rating_counts,msg_error=error )
#----------------------
#save the book rate and comment to the data base
@app.route("/saveRating/<string:isbn>",methods=["POST"])
def saveRating(isbn):
    res =requests.get("https://www.goodreads.com/book/review_counts.json",params={"key": "SpKTJPX39SYY6jb35N7A", "isbns":isbn.strip()})
     
    if res.status_code != 200:
        error = "ERROR: API request unsuccessful."
        return error
    
    
    error = ""
    data = res.json()
    outputs = data ["books"][0]
    averageRating =  str(outputs['average_rating'])  
    rating_counts =  str(outputs['work_ratings_count'])
        
    book = db.execute("select * FROM books where isbn = :isbn",{"isbn":isbn}).fetchone()
    review_view = db.execute("SELECT comment FROM reviews where isbn = :isbn",{"isbn":isbn})
    userid = session["user_id"]
    if db.execute("SELECT * FROM reviews WHERE userid = :userid and isbn =:isbn", {"userid": userid,"isbn":isbn}).rowcount == 0:
        rate = request.form.get("rate")
        comment = request.form.get('comment')
        reviewInsert = db.execute("INSERT INTO reviews(userid, isbn, rate,comment) Values (:userid,:isbn,:rate,:comment)",{"userid":userid,"isbn":isbn,"rate":rate,"comment":comment})
        db.commit()
        review_view = db.execute("SELECT comment FROM reviews where isbn = :isbn",{"isbn":isbn})
        
        
        
        
        return render_template("addReview.html",book=book,review=review_view,msg_error=error,msg="review saved successfuly",averageRating=averageRating,rating_counts=rating_counts)
      
    else:
        return render_template("addReview.html",book=book,review=review_view,msg_error="The current User already has submitted a review to this book, and cannot submit it again",averageRating=averageRating,rating_counts=rating_counts)

    
#-------------------------------------------------------------------------------------
#api route 
@app.route("/api/<string:isbn>")
def apiRoute(isbn):
    
 #create an api

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    
    if not book:
        return jsonify(status=404, error="ISBN NOT FOUND")


        #return "404 Error ISBN not found"
    
    
        #book = db.execute("SELECT * FROM books WHERE isbn = :isbn",{"isbn":isbn}).fetchone()
    count_rates = db.execute("SELECT COUNT(*) from reviews where isbn = :isbn",{"isbn":isbn}).fetchone()
    
    if int(str(count_rates[0])) == 0:
        average_score = 0.0
        count = 0;
        return jsonify({
        "title": book["title"].strip(),
        "author": book["author"].strip(),
        "year": book["year"],
        "isbn": book["isbn"],
        "review_count": count,
        "average_score": average_score })

  
     
    average_score = db.execute("SELECT avg(rate) from reviews where isbn = :isbn",{"isbn":isbn}).fetchone() 
    average = float(str(average_score[0]))
    count = db.execute("SELECT COUNT(rate) from reviews where isbn = :isbn",{"isbn":isbn}).first()
    return jsonify({
          "title": book["title"].strip(),
          "author": book["author"].strip(),
          "year": book["year"],
          "isbn": book["isbn"],
          "review_count": count[0],
          "average_score": float(average_score[0]) })
        
    
    
    
#-------------------------------------------------------------------------------------

   
       
                
