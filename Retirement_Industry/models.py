from django.db import models

# Create your models here.
class Profile_Info(models.Model):
    person_id = models.AutoField(primary_key = True)
    mail = models.EmailField(max_length=254, default = 'me@gmail.com')
    name = models.CharField(max_length = 122)
    age = models.CharField(max_length = 122)
    work_class = models.CharField(max_length = 122)
    marital_status = models.CharField(max_length = 122)
    occupation = models.CharField(max_length = 122)
    gender = models.CharField(max_length = 122)
    salary = models.IntegerField()
    password = models.CharField(max_length = 122)

    def __str__(self):
        return self.name
    
class Transaction_History(models.Model):
    transaction_id = models.AutoField(primary_key = True)
    person_id = models.IntegerField()
    transaction_name = models.CharField(max_length=122)
    transaction_amount = models.IntegerField()
    expense_category = models.CharField(max_length = 122)
    rounded_off_amount = models.IntegerField()

    def __str__(self):
        return self.transaction_name

class Current_Investment(models.Model):
    person_id = models.IntegerField()
    scheme_name = models.CharField(max_length=122)
    investment_amount = models.IntegerField()
    policy_term = models.CharField(max_length=500)
    date_of_investment = models.CharField(max_length = 122)
    rate_of_interest = models.IntegerField()
    def __str__(self):
        return self.scheme_name
