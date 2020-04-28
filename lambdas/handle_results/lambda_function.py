import json
import boto3
import os
from collections import defaultdict
import pprint
import pymysql
import uuid

class Committee(object):
    def __init__(self, connection):
        self.attributes = {}
        self.connection = connection
        self.table_name = "Committees"
        self.identifying_attr = "name"
    
    def addAttribute(self, attribute, value):
        self.attributes[attribute] = value
        
        if attribute == self.identifying_attr:
            self.attributes['id'] = self.getID()
        
    def getID(self):
        if self.identifying_attr not in self.attributes:
            return -1
            
        if 'id' in self.attributes:
            return self.attributes['id']
    
        result = self.connection.execute("select id," + self.identifying_attr + " from " + 
                                            self.table_name + " WHERE " +
                                            self.identifying_attr + " = '" + self.attributes[self.identifying_attr] + "';")
        if result == 0:       
            self.attributes['id'] = str(uuid.uuid4())
        else:
            self.attributes['id'] = self.connection.fetchone()[0]  
        
        return self.attributes['id']
    def runInsertionQuery(self):
        if self.identifying_attr not in self.attributes:
            return -1
    
        self.getID()
        
        value_names_str = "(" + ','.join([x for x in self.attributes]) + ")"
        
        values_str = "values ("
        update_values_str = ""
        for attr in self.attributes:
            if isinstance(self.attributes[attr], float):
                values_str += self.attributes[attr] + ","
                if attr != self.identifying_attr:
                    update_values_str += attr + " = " + self.attributes[attr] + ","
            else:
                values_str += "'" + self.attributes[attr] + "',"
                if attr != self.identifying_attr:
                    update_values_str += attr + " = '" + self.attributes[attr] + "',"
        
        values_str = values_str[:-1] + ")"
        update_values_str = update_values_str[:-1]
        statement = 'insert into ' + self.table_name + \
                    ' ' + value_names_str + \
                    ' ' + values_str + " on duplicate key update " + \
                    update_values_str + ";"
    
        print(statement)
        self.connection.execute(statement)
        return 1
        
class Contract(object):
    def __init__(self, connection):
        self.attributes = {}
        self.connection = connection
        self.table_name = "Contracts"
        self.identifying_attr = "contract_number"
        self.committee = None
        self.buyer = None
    
    def addAttribute(self, attribute, value):
        self.attributes[attribute] = value
        
        if attribute == self.identifying_attr:
            self.attributes['id'] = self.getID()
        
    def getID(self):
        if self.identifying_attr not in self.attributes:
            return -1
            
        if 'id' in self.attributes:
            return self.attributes['id']
    
        result = self.connection.execute("select id," + self.identifying_attr + " from " + 
                                            self.table_name + " WHERE " +
                                            self.identifying_attr + " = '" + self.attributes[self.identifying_attr] + "';")
        if result == 0:      
            self.attributes['id'] = str(uuid.uuid4())
        else:
            self.attributes['id'] = self.connection.fetchone()[0]  
        
        return self.attributes['id']
            
    def runInsertionQuery(self):
        if self.identifying_attr not in self.attributes:
            self.attributes['contract_number'] = str(uuid.uuid4())
        
        self.getID()
        
        if self.committee != None:
            self.attributes['committee_id'] = self.committee.getID()
            
        if self.buyer != None:
            self.attributes['buyer_id'] = self.buyer.getID()
        
        value_names_str = "(" + ','.join([x for x in self.attributes]) + ")"
        
        values_str = "values ("
        update_values_str = ""
        for attr in self.attributes:
            if isinstance(self.attributes[attr], float):
                values_str += self.attributes[attr] + ","
                if attr != self.identifying_attr:
                    update_values_str += attr + " = " + self.attributes[attr] + ","
            else:
                values_str += "'" + self.attributes[attr] + "',"
                if attr != self.identifying_attr:
                    update_values_str += attr + " = '" + self.attributes[attr] + "',"
        
        values_str = values_str[:-1] + ")"
        update_values_str = update_values_str[:-1]
        statement = 'insert into ' + self.table_name + \
                    ' ' + value_names_str + \
                    ' ' + values_str + " on duplicate key update " + \
                    update_values_str + ";"
    
        print(statement)
        self.connection.execute(statement)
        return 1
        
        
class Buyer(object):
    def __init__(self, connection):
        self.attributes = {}
        self.connection = connection
        self.table_name = "Buyers"
        self.identifying_attr = "agency"
    
    def addAttribute(self, attribute, value):
        self.attributes[attribute] = value
        
        if attribute == self.identifying_attr:
            self.attributes['id'] = self.getID()
        
    def getID(self):
        if self.identifying_attr not in self.attributes:
            return -1
            
        if 'id' in self.attributes:
            return self.attributes['id']
    
        result = self.connection.execute("select id," + self.identifying_attr + " from " + 
                                            self.table_name + " WHERE " +
                                            self.identifying_attr + " = '" + self.attributes[self.identifying_attr] + "';")
        
        if result == 0:    
            self.attributes['id'] = str(uuid.uuid4())
        else:
            self.attributes['id'] = self.connection.fetchone()[0]        
        return self.attributes['id']
            
    def runInsertionQuery(self):
        if self.identifying_attr not in self.attributes:
            return -1
    
        
        self.getID()
        
        value_names_str = "(" + ','.join([x for x in self.attributes]) + ")"
        
        values_str = "values ("
        update_values_str = ""
        for attr in self.attributes:
            if isinstance(self.attributes[attr], float):
                values_str += self.attributes[attr] + ","
                if attr != self.identifying_attr:
                    update_values_str += attr + " = " + self.attributes[attr] + ","
            else:
                values_str += "'" + self.attributes[attr] + "',"
                if attr != self.identifying_attr:
                    update_values_str += attr + " = '" + self.attributes[attr] + "',"
        
        values_str = values_str[:-1] + ")"
        update_values_str = update_values_str[:-1]
        statement = 'insert into ' + self.table_name + \
                    ' ' + value_names_str + \
                    ' ' + values_str + " on duplicate key update " + \
                    update_values_str + ";"
        print(statement)
        self.connection.execute(statement)
        return 1

def lambda_handler(event, context):
    #HANDLE RESULTS
    #jpgbucket = os.environ['JPG_BUCKET']
    #templatebucket = os.environ['TEMPLATE_BUCKET']
    status = event['returnStatus']
    body = event['body']
    document = event['document']
    bucket = event['jpgbucket']
    if status == 'complete':
        print("Parsing completed.")
        s3 = boto3.client('s3')
        s3.delete_object(Bucket=bucket, Key=document + ".pdf")
        
        jpg_doc = document.split("/")
        jpg_doc[0] = "jpg"
        del jpg_doc[-1]
        jpg_doc = "/".join(jpg_doc)
        print(jpg_doc)
        jpg_list = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=jpg_doc
        )
        jpg_list = [item['Key'] for item in jpg_list['Contents'] if item['Key'][-4:] == ".jpg"]
        
        
        for jpg in jpg_list:
            s3.delete_object(Bucket=bucket, Key=jpg)
        
        try:
            rds_host = "fcc-opif.cv8m2mda4hsq.us-east-2.rds.amazonaws.com"
            user_name = "octo_guacamole"
            password = "P0Y3t!1raFQK"
            db_name = "ReFreeTheFiles"
            conn = pymysql.connect(rds_host, user=user_name, passwd=password, db=db_name, connect_timeout=5)
        except pymysql.MySQLError as e:
            print("ERROR: Unexpected error: Could not connect to MySQL instance.")
            print(e)
            return {'returnStatus':'error'}
            
        committee = Committee(conn.cursor())
        buyer = Buyer(conn.cursor())
        contract = Contract(conn.cursor())
        contract.committee = committee
        contract.buyer = buyer
        
        for label in body:
            print(label)
            if body[label]['handwritten'] == False and body[label]['text'] != "":
                keywords = label.split('/')
                
                table = keywords[0]
                field = keywords[1]
                value = body[label]['text']
                
                if table == "Committees":
                    committee.addAttribute(field, value)
                if table == "Buyers":
                    buyer.addAttribute(field, value)
                if table == "Contracts":
                    if field in ['gross_amount', 'commission_amount']:
                        buyer.addAttribute(field, float(value))
                    elif field in ['fcc_file_id', 'number_of_spots']:
                        buyer.addAttribute(field, int(value))
                    else:
                        buyer.addAttribute(field, value)
        
        committee.runInsertionQuery()
        buyer.runInsertionQuery()
        contract.runInsertionQuery()
        conn.commit()
        conn.close()
        return {
            'statusCode': 200,
            'returnStatus': 'success'
        }
    elif status == 'incomplete':
        print("Templates missing for some pages.")
        print(body)
        return {
            'statusCode': 200,
            'returnStatus': 'failure'
        }
    else:
        print("Parsing failed.")
        return {
            'statusCode': 200,
            'returnStatus': status
        }