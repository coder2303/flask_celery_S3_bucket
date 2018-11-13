from flask import Flask, render_template, request
from flask.ext.uploads import UploadSet, configure_uploads, IMAGES
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
import os
import boto3

app = Flask(__name__)
photos = UploadSet('photos', IMAGES)
app.config['UPLOADED_PHOTOS_DEST'] = 'static/img' # destination of upload photo
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///students.sqlite3'
app.config['SECRET_KEY'] = "random string"
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0' # broker url
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery('coalition_python', broker=app.config['CELERY_BROKER_URL'],include=['coalition_python'])
celery.conf.update(app.config)
configure_uploads(app, photos)

db = SQLAlchemy(app) # use SQLAlchemy for ORM

# create a ORM database of image
class image(db.Model):
   id = db.Column('image_id', db.Integer, primary_key = True) # id of the image
   img_name = db.Column(db.String(100)) # image name
   size = db.Column(db.String(50))  # image size

   
   def __init__(self, img_name, size):
       self.img_name = img_name
       self.size = size

   
db.create_all()    # create the database





@app.route('/') # use to show all the images store in the image DB
def show_all():
   return render_template('images.html', image = image.query.all() )



# upload the image to the DB and to S3 Bucket using celery
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST' and 'photo' in request.files:
        img_file = photos.save(request.files['photo'])
        img_size=os.stat('static/img/'+img_file).st_size
        images = image(img_file,img_size) # creating the image element 
        upload_img_bucket.delay(img_file) # uploade the image to S3 Bucket
        
        db.session.add(images) # storing the image to DB
        db.session.commit()
        
        return 'This '+img_file + ' is Uploaded to the S3'
    return render_template('upload.html')


# delete the row for given id
@app.route('/del_data',methods=['GET', 'POST'])
def del_data():
    if request.method == 'POST':
          get_id=request.form['id']
          image.query.filter(image.id == get_id).delete()
          db.session.commit()
          return "Item is deleted sucessfully"
          
    return render_template('delete_id.html')    
        

@celery.task  # function that will run in background
def upload_img_bucket(img_file):
        s3=boto3.client('s3','us-west-2')
        s3.upload_file('static/img/'+img_file,'coalitionbucket',img_file)


if __name__ == '__main__':
    db.create_all()
    app.debug=True
    app.run(host='0.0.0.0',port=5000)
    