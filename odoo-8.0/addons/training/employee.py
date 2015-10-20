class employee:
    empcount=0
    def __init__(self,name,age):
        self.name=name
        self.age=age
        employee.empcount+=1
        
    def display(self):
        print "name" ,self.name
        print "age",self.age
        print "employee count",employee.empcount
        

emp1=employee("zara",10)
emp1.display()
emp2=employee("vanheusen",20)
emp2.display()
