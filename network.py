# -*- coding: Utf-8 -*
# Author: aurelien.esnard@u-bordeaux.fr
import socket
import time
import errno
import random
from model import *
import pygame
import sys
import threading


class color:
   PURPLE = '\033[95m'
   CYAN = '\033[96m'
   DARKCYAN = '\033[36m'
   BLUE = '\033[94m'
   GREEN = '\033[92m'
   YELLOW = '\033[93m'
   RED = '\033[91m'
   BOLD = '\033[1m'
   UNDERLINE = '\033[4m'
   END = '\033[0m'

################################################################################
#                          NETWORK SERVER CONTROLLER                           #
################################################################################

#This function send current model to the client socket
#Fruits,characters,bombs infos
def send_model(socket_client,model):
      data_str = ""
      data_str+= "Map|"+str(model.map.width)+"|"+str(model.map.height)+"\n"
      for fruit in model.fruits:
            data_str += "Fruit|"+str(fruit.kind)+"|"+str(fruit.pos[X])+"|"+str(fruit.pos[Y])+"|"+"\n"
      for character in model.characters:
            data_str += "Char|"+str(character.kind)+"|"+str(character.health)+"|"+str(character.immunity)+"|"+str(character.disarmed)+"|"+str(character.nickname)+"|"+str(character.pos[X])+"|"+str(character.pos[Y])+"|"+str(character.direction)+"\n"
      for bomb in model.bombs:
            data_str += "Bomb|"+str(bomb.pos[X])+"|"+str(bomb.pos[Y])+"|"+str(bomb.max_range)+"|"+str(bomb.countdown)+"|"+str(bomb.time_to_explode)+"\n"
      #print(data_str)
      socket_client.sendall((data_str).encode())
# decode & split the message into list , return it
def split_message(message,w):
    message=message.decode()
    splited_list=message.split(w)
    #print(splited_list)
    return splited_list

##Server Class
def g (self):
   while(1):
         data=sys.stdin.readline()
         L_data = data.split("\n")
         if "KILL|" in L_data[0]:
            liste_data = L_data[0].split("|")
            if len(liste_data)==2:
               if self.model.look(liste_data[1]):
                         self.model.kill_character(liste_data[1])
                         for s in list(self.co_client.keys()): 
                           #Pour éviter RuntimeError: dictionary changed size during iteration ,  il faut passer par une liste des keys
                                 if s==liste_data[1]:
                                     del self.co_client[s]
                                 else:
                                     self.co_client[s].sendall(("KILL|"+liste_data[1]+"\n").encode())
               
            
class NetworkServerController:

    def __init__(self, model, port):
        self.nb_client=0; #Nb of clients
        self.co_client={} #dictionnaire_connexions
        self.model = model
        self.port = port
        self.countdown = random.randint(6000, 15000)
        #####Création du socket###############
        self.main_co = socket.socket(socket.AF_INET6,socket.SOCK_STREAM )
        self.main_co.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        ## Liaison socket adresse spécifique ##
        self.main_co.bind(('',port))
        ## Attente requete client // écoute ##
        self.main_co.listen(1)
        ## Débloquer le socket ##
        self.main_co.setblocking(False)
        THREAD2 =threading.Thread(None,g,None,(self,))
        #FERME LE THREAD QUAND IL NE RESTE PLUS QUE LUI
        THREAD2.daemon = True
        THREAD2.start()

    # time event

    def tick(self, dt):
        #On établit la connexion:
        newcomer = False
        try:
            new_co,adress=self.main_co.accept()
            newcomer = True
        # cas d'erreur
        except socket.error as e:
            if not (e.args[0] == errno.EWOULDBLOCK):
                print("error:", e)
        # On enregistre la connexion dans le dictionnaire
        if newcomer:
            self.nb_client += 1
            #Reception du pseudo du nouveau client
            pseudo = new_co.recv(30).decode()
            is_name_valid = False
            while not is_name_valid:
                  character = self.model.look(pseudo)
                  if character:
                        rnd = random.randint(0, 999)
                        pseudo = pseudo+str(rnd)
                  else:
                        is_name_valid = True
                        new_co.sendall(("NewName|"+pseudo+"\n").encode())
            #envoi de message de bienvenue
            new_co.sendall("Yo ma caille, installe toi !\n".encode())
            #création personnage
            new_char = self.model.add_character(pseudo, isplayer = False)
            #on enregistre le nouveau client dans le dictionnaire , la clé est son pseudo
            self.co_client[pseudo] = new_co
        #réception d'éventuelle commandes
        data_str = ""
        received = False
        #Chaque socket client devient non bloquant
        for s in self.co_client:
            self.co_client[s].setblocking(False)
            try:
                #On receptionne le message
                data_str += (self.co_client[s].recv(3000)).decode()
                received = True
                #print(data_str)
                #cas d'erreur
            except socket.error as e:
                  if not (e.args[0] == errno.EWOULDBLOCK):
                      print("error:", e)
        ## test bomb explode(fonctionnel) ##
            for c in self.model.characters:
                  for bomb in self.model.bombs:
                        c.explosion(bomb)
        if received:
            liste_task = split_message(data_str.encode(),"\n")
            #Chaque section est séparé par \n ( ex: Fruit | x | y \n Bomb|....)
            for string in liste_task:
                liste_data = split_message(string.encode(),"|")
                
                if liste_data[0] == "KILL": #Si le joueur procède à une déconnexion
                    #Si correspond au joueur en deconnexion , le tue .
                      if self.model.look(liste_data[1]):
                         self.model.kill_character(liste_data[1])
                      for s in list(self.co_client.keys()): 
                        #Pour éviter RuntimeError: dictionary changed size during iteration ,  il faut passer par une liste des keys
                              if s==liste_data[1]:
                                  del self.co_client[s]
                              else:
                                  self.co_client[s].sendall(("KILL|"+liste_data[1]+"\n").encode())
                #Chaque information est séparé par une |
                if liste_data[0] == "Move":
                      for c in self.model.characters:
                            if c.nickname == liste_data[1]:
                                  c.move(int(liste_data[2]), self.model.bombs)     
                if liste_data[0] == "MSG" :
                       for s in self.co_client: # On envoie l'information qu'un joueur a déposé une bombe
                             print(liste_data)
                             self.co_client[s].sendall(("MSG|"+liste_data[2]+":"+liste_data[1]+"\n").encode())
                if liste_data[0] == "CMD":
                      #print(liste_data)
                   
                      if liste_data[1]=="fruitpop":
                            for _ in range(random.randint(4,14)): self.model.add_fruit()
                            for s in self.co_client: # On envoie l'information qu'un joueur a déposé une bombe
                                   data = ""
                                   for fruit in self.model.fruits:
                                         data += "Fruit|"+str(fruit.kind)+"|"+str(fruit.pos[X])+"|"+str(fruit.pos[Y])+"|"+"\n"
                                   self.co_client[s].sendall(("CMD|fruitpop"+"\n"+data).encode())
                      if liste_data[1] == "random":
                            for c in self.model.characters:
                                  for i in range(random.randint(2,8)):
                                        c.move(random.randint(0,3),self.model.bombs)
                      if liste_data[1] == "list":
                            
                           pseudos = "Currents players are : "
                           for i in self.co_client.keys():
                                 pseudos += i+","
                           self.co_client[liste_data[2]].sendall(("CMD|list"+"|"+pseudos+"\n").encode()) 
                      if liste_data[1] == "skin":
                           for c in self.model.characters:
                              if c.nickname == liste_data[2]:
                                 new= random.choice(CHARACTERS)
                                 while (c.kind) == new:
                                    new=random.choice(CHARACTERS)
                                 c.kind = new
                                 for s in self.co_client:
                                    self.co_client[s].sendall(("CMD|skin|"+liste_data[2]+"|"+str(c.kind)+"\n").encode())
                            
                if liste_data[0] == "BOMB":
                   for c in self.model.characters:
                        if c.nickname == liste_data[1]:
                            self.model.drop_bomb(liste_data[1])
                            for s in self.co_client: # On envoie l'information qu'un joueur a déposé une bombe
                                  self.co_client[s].sendall(("BOMB|"+c.nickname+"\n").encode())

        #Envoie d'une bombe sur un client au hasard si countdown arrive à <= 0
        self.countdown -= dt
        if self.countdown <= 0 and self.nb_client > 0:
              which_one = random.randint(0, self.nb_client-1)
              count = 0
              for c in self.model.characters:
                    if which_one == count:
                          disarmed_save = c.disarmed
                          c.disarmed = 0
                          self.model.drop_bomb(c.nickname)
                          c.disarmed = disarmed_save
                          for s in self.co_client:
                                self.co_client[s].sendall(("HBOMB|"+c.nickname+"\n").encode())
                    count += 1
              self.countdown = random.randint(6000, 15000)    

        #Envoie le model à chaque tick à chaque client
        for s in self.co_client:

            send_model(self.co_client[s],self.model)
            self.has_send = True
        return True

################################################################################
#                          NETWORK CLIENT CONTROLLER                           #
################################################################################

def f(serv,pseudo,limit_CMD):
      while(1):
         data=sys.stdin.readline()
         if limit_CMD < 4: 
            if "CMD" in data:
               #print(data)
               l=data.split("\n")
               serv.sendall(((l[0])+"|"+pseudo+"\n").encode())
               limit_CMD +=1
         else:
            print(color.RED + " Vous avez atteint votre quota de commandes ( Vous pouvez en utilisez 4 maximum par soucis d'équilibrage ) " + color.END)
         if "MSG" in data :
               #print(pseudo)
               l=data.split("\n")
               serv.sendall((l[0]+"|"+pseudo+"\n").encode())

class NetworkClientController:

    def __init__(self, model, host, port, nickname):
        self.model = model
        self.host = host
        self.port = port
        self.nickname = nickname
        self.limiteCMD= 0
        self.etat_fruit=False
        self.etat_bombs=False
        self.etat_connexion=False
        #création du socket :
        self.co_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.co_serveur.connect((host, port))
        #Débloquage du socket_client
        self.co_serveur.setblocking(False)
        #envoie pseudo
        self.co_serveur.send(nickname.encode())
        THREAD =threading.Thread(None,f,None,(self.co_serveur,self.nickname,self.limiteCMD))
        #FERME LE THREAD QUAND IL NE RESTE PLUS QUE LUI
        THREAD.daemon = True
        THREAD.start()
        print(color.BOLD + color.DARKCYAN + " Pour envoyer un message aux autres joueurs , préfixer le par MSG| ( exemple : MSG|coucou ça va ) \n" + color.END)
        print(color.BOLD + color.DARKCYAN + " Vous disposez dans la limite de 4 , de commandes fun à rentrer dans le terminal , préfixer le par CMD| \n puis rentrer aux choix selon 4 options possibles : fruitpop , skin , random , list )  ( exemple : CMD|fruitpop ) \n" + color.END)
        print(color.BOLD + color.DARKCYAN + " fruitpop fait tomber des fruits ; skin change le costume de votre personnage ; random fait déplacer tous les personnages aléatoirement , list donne la liste des joueurs  \n" + color.END)

        #récupère message de bienvenue
        try:
            message=self.co_serveur.recv(30)
            #print(message.decode())
        # cas d'erreur
        except socket.error as e:
              if not (e.args[0] == errno.EWOULDBLOCK):
                  print("error:", e)

    # keyboard events

    def keyboard_quit(self):
        #print("=> event \"quit\"")
        a=("KILL|"+self.nickname+"|"+"\n").encode()
        #communique au serveur qu'il doit retirer le personnage
        self.co_serveur.sendall(a)
        #Shutdown de la connexion
        self.co_serveur.shutdown(1)
        #finalement close le socket
        self.co_serveur.close()

        return False

    def keyboard_move_character(self, direction):
        #print("=> event \"keyboard move direction\" {}".format(DIRECTIONS_STR[direction]))
        data_str = "Move|"+self.nickname+"|"+str(direction)+"\n"
        #Envoie quel personnage procède à un mouvement ainsi que sa direction
        #print(data_str)
        self.co_serveur.sendall(data_str.encode())
        return True

    def keyboard_drop_bomb(self):
        #print("=> event \"keyboard drop bomb\"")
        #Envoie au serveur qui a posé une bombe
        data_str = ("BOMB|"+self.nickname+"\n")
        #print(data_str)
        self.co_serveur.sendall(data_str.encode())
        # ...
        return True

    # time event

    def tick(self, dt):
        #recupère liste de donnée
        #Si client prefixe son message par MSG| , envoie le message aux autres clients & serveur
        #Si client prefixe son message par CMD| , déclenche une commande serveur si existe
        
        received = False
        try:
            message=self.co_serveur.recv(3000)
            if message != b'':
                  received = True
                  liste_task=split_message(message,"\n")
                  #print(message)
            else:
                  print("\nLa connexion au serveur distant a été interrompue!\n")
                  sys.exit()
        # cas d'erreur
        except socket.error as e:
              if not (e.args[0] == errno.EWOULDBLOCK):
                  print("error:", e)
        if received:
              #print(liste_task)
              for i in range(len(liste_task)):
                  # chaque information est split avec une |
                  liste_data = split_message(liste_task[i].encode(),"|")
                  #print(liste_data)
                  if liste_data[0] =="CMD":
                        if liste_data[1] == "fruitpop":
                              self.etat_fruit=False
                        if liste_data[1] == "list":
                              print(color.PURPLE + color.BOLD + liste_data[2] + color.END)
                        if liste_data[1]== "skin":
                            for c in self.model.characters:
                                print(liste_data[2])
                                if liste_data[2] == c.nickname:
                                   c.kind = int(liste_data[3])
                              
                  elif liste_data[0] == "Fruit" and not self.etat_fruit:
                        self.model.add_fruit(int(liste_data[1]), (int(liste_data[2]), int(liste_data[3])))
                  elif liste_data[0] == "Bomb" and not self.etat_bombs:
                        self.model.bombs.append(Bomb(self.model.map, (int(liste_data[1]), int(liste_data[2])), int(liste_data[5])))
                  elif liste_data[0] == "NewName":
                        self.nickname = liste_data[1]
                  elif liste_data[0]=="Map":
                        # CAS MAP 1 RECU PAR SERVEUR
                        if self.model.map.width != int(liste_data[1]) and self.model.map.height!=int(liste_data[2]):
                              if int(liste_data[1])==25 and int(liste_data[2])==13:
                                    self.model.load_map("maps/map1")
                                    pygame.display.set_mode((int(liste_data[1])*30,int(liste_data[2])*30))
                       # CAS MAP 0 RECU PAR SERVEUR
                              if int(liste_data[1])==13 and int(liste_data[2])==11:
                                    self.model.load_map("maps/map0")
                  
                  elif liste_data[0] == "Char":
                        addIt = True
                        for c in self.model.characters:
                              #print("------> ",self.model.player)
                              if c.nickname == liste_data[5]:
                                    addIt = False
                                    #print(c.pos)
                                    #ASSIGNEMENT DIRECTION ET POSITION PERSONNAGE RECU PAR SERVEUR
                                    c.direction=int(liste_data[8])
                                    c.pos = (int(liste_data[6]),int(liste_data[7]))
                        #Détermine quel character est celui client
                        if self.nickname == liste_data[5]:
                              isPlayer = True
                        else:
                              isPlayer = False
                        if addIt:
                              self.model.add_character(liste_data[5], isPlayer, int(liste_data[1]), (int(liste_data[6]), int(liste_data[7])))
                  elif liste_data[0]=="MSG":
                        print(color.BOLD + liste_data[1] + color.END)
                  elif liste_data[0]=="KILL":
                        if self.model.look(liste_data[1]):
                              self.model.kill_character(liste_data[1])
                        print(color.BOLD+color.RED+"Le joueur "+liste_data[1] + "ne fais plus partie de ce monde \n " + color.END)
                  #if liste_data[0]="Bomb":
                  elif liste_data[0] == "BOMB":   # Je me suis directement envoyer le pseudo ( c'est le seul argument qu'on a besoin pour drop) au moment où je reçois requête client , c'est quasi instant
                        self.model.drop_bomb(liste_data[1])
                        break
                  elif liste_data[0] == "HBOMB":   # Je me suis directement envoyer le pseudo ( c'est le seul argument qu'on a besoin pour drop) au moment où je reçois requête client , c'est quasi instant
                        for c in self.model.characters:
                              if c.nickname == liste_data[1]:
                                    save_disarmed = c.disarmed
                                    c.disarmed = 0
                                    self.model.drop_bomb(liste_data[1])
                                    c.disarmed = save_disarmed
                                    break
              if not self.etat_connexion:
                 cpt=0
                 for c in self.model.characters:
                    cpt+=1
                 print(color.BOLD + color.YELLOW + " Il y'a actuellement  " + str(cpt) + "  joueurs connectés" + color.END)
                 
                 
              self.etat_fruit=True
              self.etat_bombs=True
              self.etat_connexion=True

        #time.sleep(0.5)
        return True

			
