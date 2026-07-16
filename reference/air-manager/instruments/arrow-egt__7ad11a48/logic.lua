img_add_fullscreen("BG.png")




--------------------------------------------------------------FUEL Consumption------------------------------------------------------------------------------------

---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 366                   --> Y-Koordinate des Kreismittelpunktes
x       = - 30                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y     = - 17                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
x_24       = - 25                   --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG des Wertes 24
y_24     =  - 7                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG des Wertes 24
x_PSI       = - 35                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG für den Grenzdruck 19 PSI
y_PSI     = -23                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG für den Grenzdruck 19 PSI
R_Skale12  = 200                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 - 0       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12 + 0      --> Radius der Stopstrich
R_BG      = R_Skale12 + 45      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 40     --> Radius des GREEN ARCS
R_arc_w   = R_Skale12 + 2     --> Radius des GREEN ARCS

R_Beschr  = R_Skale12 - 15        --> Radius der Beschriftung

EGT_min    = 1200       --> minimal angezeigte MAP
EGT_max    = 1700       --> maximal angezeigte MAP
EGT_Delta  = EGT_max - EGT_min

EGT_g_1    = 1200        --> Startwert GREEN ARC
EGT_g_2    = 1650       --> Endwert GREEN ARC

MUV      = 100        --> Main-Unit-Value (1. Skale)

N            = EGT_Delta/MUV   --> Anzahl der Werte/Striche im Kreis
OMEGA        =  - 50          --> Skalendrehung um XY Grad )( O Grad ist im Norden der Anzeige)
h               = 1       --> Stauchung der Skalierung (Exponent)
ZWEI_PI_nichtnormiert = 100 --> Grad-Nutzung der Skale
ZWEI_PI      = (ZWEI_PI_nichtnormiert)^(1/h)   --> Grad-Nutzung der Skale
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/4     --> Skalenabstand 1. und 2. Skale
StrL1       = 31         --> Strichlänge (Haupt-Skala Striche)
StrL2        = 20         --> Strichlänge (SUB-Skalaj Striche)
StrL_Stop    = 49.5

j = 0
s = ""
---------------------------------------------------------------------------
  --------- grüner Bogen -------------------
canvas_add(0, 0, 512, 512, function()
    Alpha_1 = (ZWEI_PI/EGT_Delta * (EGT_g_1 - EGT_min))^(h) + OMEGA - 90
    Alpha_2 = (ZWEI_PI/EGT_Delta * (EGT_g_2 - EGT_min))^(h) + OMEGA - 90
    Alpha_max = (ZWEI_PI/EGT_Delta * (EGT_max- EGT_min))^(h) + OMEGA - 90
    print(EGT_g_1, Alpha_1, EGT_g_2, Alpha_2)
    
    r = 0.78 ----> Korrekturwinkel zum Ausgleich der Strichdicke der Hauptskale
    
   _arc(X_c, Y_c, Alpha_1 - r , Alpha_2,R_arc_g)
  _stroke("green", 19)
   _arc(X_c, Y_c, Alpha_1, Alpha_max,R_arc_w)
  _stroke("white", 4) 
              
end)

  

---------------------------------------------------------------------------
    N = tonumber(N)
    while(j <= N )
        do
-----------------   1. Skale   ----------------
                
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
					Y = math.cos(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
					d = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL1)) + X_c
					p = math.cos(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL1)) + Y_c   
                
						Stroke = canvas_add(0, 0, 512, 512, function()
							_move_to(X, Y)
							_line_to(d, p)
							_stroke("white", 5)
						end)

-----------------   Subskale-Skale   ----------------   
                                     
                    k = 1
                    while(k <=  3) -- Anzahl der Zwischenstriche z.B.: 1..4 (Strichwert = 100; Bei 4 kurzen Strichen, der 5. ist bereits ein langer Strich)
                    do
                    
                        if j == N then
                        
                        else
    
                                ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                                X = math.sin(((PHI2 * k + PHI1 * j)^(h) + OMEGA)/ 360 * 2 * math.pi) * ( 1 * R_Skale3) + X_c
                                Y = math.cos(((PHI2 * k + PHI1 * j)^(h) + OMEGA)/ 360 * 2 * math.pi) * (-1 * R_Skale3) + Y_c
                                d = math.sin(((PHI2 * k + PHI1 * j)^(h) + OMEGA)/ 360 * 2 * math.pi) * ( 1 * (R_Skale3 + StrL2)) + X_c
                                p = math.cos(((PHI2 * k + PHI1 * j)^(h) + OMEGA)/ 360 * 2 * math.pi) * (-1 * (R_Skale3 + StrL2)) + Y_c
                                
                                Stroke = canvas_add(0, 0, 512, 512, function()
                                        _move_to(X, Y)
                                        _line_to(d, p)
                                        _stroke("white", 3)
                                        end)
                        end
     
                    k = k + 1
                    end
                    

-----------------  Beschriftung   ---------------- 

                                function Digits(s)                
                                         s = tostring(var_format(((j * MUV + EGT_min)/100),0))  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                Y = math.cos(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (-1 * R_Beschr) + Y_c
                               ------ print(j, N, s, Digits(s))
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 20; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 60, 30)
                           
            			
			j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = - 100
y = -60
txt_add("EGT","font: roboto_bold.ttf; size: 60; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 50)

x = - 100
y = -15
txt_add("°F x 100","font: roboto_bold.ttf; size: 35; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 30)

  ---------roter Stopstrich  ---------------
canvas_add(0, 0, 512, 512, function()
    Alpha_3 = Alpha_2 + 90
  X = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * R_Stop) + X_c
  Y = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * R_Stop) + Y_c
  d = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * (R_Stop + StrL_Stop)) + X_c
  p = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * (R_Stop + StrL_Stop)) + Y_c   
                
  _move_to(X, Y)
  _line_to(d, p)
  _stroke("red", 4)
end)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------
x = 20
y = -130

img_needle = img_add ("needle.png",X_c - 256 + x/2 , Y_c - 256  + y/2 ,512 - x,512 - y)

function PT(EGT)
        EGT = EGT --* 1.8 + 32
        EGT = var_cap(EGT,1200,1700)
        Alpha = (ZWEI_PI/EGT_Delta * (EGT - EGT_min))^(h) + OMEGA
        print(ZWEI_PI, EGT_Delta, EGT, h, OMEGA, Alpha)
        rotate(img_needle, Alpha)
end



---------------------------------------------------------------------------------
u = 150
v = -20
w = 300

img_add("Alcor2.png",0 + u ,0 + v ,512 - w,512 - w)


u = 30
v = u

img_add("glass.png",0 + u/2 ,0 + v/2 ,512 - u,512 - v)

u = 50
v = 276
w = 100

img_add("bezel2.png",0 + u ,0 + v ,512 - w,512 - w)

u = 8
v = 5
w = 15

img_add("bezel4.png",0 + u ,0 + v ,512 - w,512 - w)

u = 10
v = u

-- img_add("bezel.png",0 + u/2 ,0 + v/2 ,512 - u,512 - v)

fs2020_variable_subscribe("GENERAL ENG EXHAUST GAS TEMPERATURE:1", "Fahrenheit", PT)
