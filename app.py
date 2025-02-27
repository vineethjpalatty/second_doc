# importing packages
from flask import Flask ,render_template, redirect, url_for, session, request, logging
import requests
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch
from torch import nn, optim
from torchvision import transforms, datasets, models
from torch.utils.data.sampler import SubsetRandomSampler
from werkzeug.utils import secure_filename
import os
from slackeventsapi import SlackEventAdapter
from slackclient import SlackClient
from slacker import Slacker
import urllib
# UPLOAD_FOLDER = '/Users/pranoy/Desktop/second_opinion/uploads/'
# ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

web_hook_url = 'https://hooks.slack.com/services/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'

slack_msg = {'text':'event_data'}

model = models.resnet50(pretrained=True)

for param in model.parameters():
    param.requires_grad = False

model.fc = nn.Linear(2048, 2, bias=True)

fc_parameters = model.fc.parameters()

for param in fc_parameters:
    param.requires_grad = True
model.load_state_dict(torch.load('checkpoints.pt',map_location='cpu'))
criterion = nn.CrossEntropyLoss()
def load_input_image(img_path):    
    image = Image.open(img_path)
    prediction_transform = transforms.Compose([transforms.Resize(size=(224, 224)),
                                     transforms.ToTensor(), 
                                     transforms.Normalize([0.485, 0.456, 0.406], 
                                                          [0.229, 0.224, 0.225])])

    # discard the transparent, alpha channel (that's the :3) and add the batch dimension
    image = prediction_transform(image)[:3,:,:].unsqueeze(0)
    return image

def predict_malaria(model, class_names, img_path):
    # load the image and return the predicted breed
    img = load_input_image(img_path)
    model = model.cpu()
    model.eval()
    idx = torch.argmax(model(img))
    
    return class_names[idx]



from glob import glob
from PIL import Image
from termcolor import colored


class_names=['Parasitized','Uninfected']


app = Flask(__name__) #app initialisation
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/android', methods=['GET','POST'])
def androidapi():
    if request.method=='POST':
        x= request.get_json()
        img_string= x['Image']
        import base64
        imagedata = base64.b64decode(img_string)
        file = "upload.png"
        with open (file,'wb') as f:
            f.write(imagedata)
        if predict_malaria(model, class_names, file) == 'Parasitized':
            flag =1 #parasite detected
        else:
            flag =0
        if flag ==1:
            print("Parasite")
            return "Parasite"
        else:
            print("No Parasite")
            return "No Parasite"
    return "Error"
@app.route('/slack', methods=['GET','POST']) #landing page intent
def slack_request():
    if request.method=='POST':
        print(request.data)
        try:
            if request.json["event"]["text"] == "Hey":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Hey, Want to test your blood sample? (yes or no)")
                return "Hey"
            elif request.json["event"]["text"] == "yes":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Hey, please upload your blood test sample")
                return "hey"
            
            elif request.json["event"]["text"] == "hey":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Hey, Want to test your blood sample? (yes or no)")
                return "hey"
            elif request.json["event"]["text"] == "no":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Stay Healthy, Have a nice day")
                return "hey"
            elif request.json["event"]["subtype"] == "bot_message":
                print("\nMessages")
                return "message"
            elif request.json["event"]["files"][0]["filetype"] == "png":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Blood Test Sample Image Found. Please wait while we are analysing the image.")
                u = request.json["event"]["files"][0]["url_private_download"]
                token = 'xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni'
                opener = urllib.request.build_opener()
                opener.addheaders = [('Authorization','Bearer '+token)]
                urllib.request.install_opener(opener)
                urllib.request.urlretrieve (u, "/home/ubuntu/second_doc/uploadedfiles/frombot.png")
                img_path = "/home/ubuntu/second_doc/uploadedfiles/frombot.png"
                if predict_malaria(model, class_names, img_path) == 'Parasitized':
                    print("Infected")
                    slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                    slackClient.chat.post_message("#general", "Infected")
                    return "Infected"
                else:
                    print("unInfected")
                    slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                    slackClient.chat.post_message("#general", "Uninfected")
                    return "Uninfected"
            elif request.json["event"]["files"][0]["filetype"] == "jpg":
                slackClient = Slacker("xoxb-577812101602-578150668373-SgUKbQ0WCgqKLtxRVvtaWbni")
                slackClient.chat.post_message("#general", "Please Input Blood sample")
                return "Uninfected"
            else:
                print("\nMessages")
                return "Hello"
        except Exception as e:
            print("Exception occured",e)
            return "Hello"
    return "Hello"

@app.route('/get_label', methods=['GET','POST']) #landing page intent
def label():
    if request.method=='POST':
        app.config['UPLOAD_FOLDER']="/home/ubuntu/second_doc/uploadedfiles/"
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        try:
            f = request.files['file']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'],f.filename))
            path = app.config['UPLOAD_FOLDER']+'/'+f.filename
            img_path = np.array(glob(path))
            # img = Image.open(img_path)
            print("REached")
            if predict_malaria(model, class_names, img_path) == 'Parasitized':
                return "Infected"
            else:
                return "Un-Infected"
        except:
            print("error")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET','POST'])
def home():
    if request.method=='POST':
        app.config['UPLOAD_FOLDER']="/home/ubuntu/second_doc/uploadedfiles/"
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        # try:
        f = request.files['file']
        f.save(os.path.join(app.config['UPLOAD_FOLDER'],f.filename))
        path = app.config['UPLOAD_FOLDER']+f.filename
        img_path = path

        if predict_malaria(model, class_names, img_path) == 'Parasitized':
            print("Infected")
            return render_template("resultinfected.html")
        else:
            print("unInfected")
            return render_template("resultuninfected.html")
        # except Exception as e:
        #     print(e)
    return render_template("index.html") #display the html template

if __name__=='__main__':
	app.run(debug=False,host="0.0.0.0",port=80) 
    #use threaded=True instead of debug=True for production
    # use port =80 for using the http port



#sample code for form data recieve
# request.form['name']
# Sample Code for JSON send data to api

#url = 'URL_FOR_API'
#data = {'TimeIndex':time1 ,'Name':name,'PhoneNumber':phone}
#headers = {'content-type': 'application/json'}
#r=requests.post(url, data=json.dumps(data), headers=headers)
#data = r.json()
#print(data)


#Sample code for JSON recieve data from API

#url = 'URL_FOR_API'
#headers = {'content-type': 'application/json'}
#r=requests.get(url, headers=headers)
#data = r.json()
#count = data['Count']
