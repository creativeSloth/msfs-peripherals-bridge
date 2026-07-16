img_add_fullscreen("BG.png")

---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 256                   --> Y-Koordinate des Kreismittelpunktes
x       = -30                   --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y       = -15                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
R_Skale12  = 170                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 + 6       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12 - 10      --> Radius der Stopstrich
R_BG      = R_Skale12 + 40      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 25     --> Radius des GREEN ARCS
R_Beschr  = R_Skale12 - 40       --> Radius der Skale

v_max    = 3500       --> maximal angezeigte Geschwindigkeit
v_g_1    = 500        --> Startwert GREEN ARC
v_g_2    = 2650       --> Endwert GREEN ARC
MUV      = 500        --> Main-Unit-Value (1. Skale)


N            = var_format(v_max/MUV, 0)   --> Anzahl der Werte/Striche im Kreis
ZWEI_PI      = 290            --> Grad-Nutzung der Skale
OMEGA        = 215          --> Skalendrehung um XY Grad
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/5     --> Skalenabstand 1. und 2. Skale
StrL1       = 30         --> Strichlänge (10er Striche)
StrL2        = 24         --> Strichlänge (5er Striche)
StrL_Stop    = 40


j = 0
local s = ""
---------------------------------------------------------------------------
  --------- grüner Bogen -------------------
canvas_add(0, 0, 512, 512, function()
    Alpha_1 = ZWEI_PI/v_max * v_g_1 + OMEGA - 90
    Alpha_2 = ZWEI_PI/v_max * v_g_2 + OMEGA - 90
   _arc(X_c, Y_c, Alpha_1, Alpha_2,R_arc_g)
  _stroke("green", 10)

  ---------roter Stopstrich  ---------------
  Alpha_3 = Alpha_2 + 90
  X = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * R_Stop) + X_c
  Y = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * R_Stop) + Y_c
  d = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * (R_Stop + StrL_Stop)) + X_c
  p = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * (R_Stop + StrL_Stop)) + Y_c   
                
  _move_to(X, Y)
  _line_to(d, p)
  _stroke("red", 5)
  
end)




---------------------------------------------------------------------------
    N = tonumber(N)
    while(j <= N ) -- 0..11 (Bei 12 Werten)
        do
-----------------   1. Skale   ----------------
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                X = math.sin((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL1)) + X_c
                p = math.cos((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL1)) + Y_c   
                
                    Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("white", 3)
                    end)

                    -----------------   Subskale-Skale   ----------------   
                                     
                    k = 1
                    while(k <=  4) -- Anzahl der Zwischenstriche z.B.: 1..4 (Strichwert = 100; Bei 4 kurzen Strichen, der 5. ist bereits ein langer Strich)
                    do
                        if j == N then
                        
                        else
                             ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                            X = math.sin((PHI2 * k + PHI1 * j + OMEGA)/ 360 * 2 * math.pi) * ( 1 * R_Skale3) + X_c
                            Y = math.cos((PHI2 * k + PHI1 * j + OMEGA)/ 360 * 2 * math.pi) * (-1 * R_Skale3) + Y_c
                            d = math.sin((PHI2 * k + PHI1 * j + OMEGA)/ 360 * 2 * math.pi) * ( 1 * (R_Skale3 + StrL2)) + X_c
                            p = math.cos((PHI2 * k + PHI1 * j + OMEGA)/ 360 * 2 * math.pi) * (-1 * (R_Skale3 + StrL2)) + Y_c
                            
                            Stroke = canvas_add(0, 0, 512, 512, function()
                                    _move_to(X, Y)
                                    _line_to(d, p)
                                    _stroke("white", 1)
                            end)
                        end
     
                                k = k + 1
                    end
                    

-----------------  Beschriftung   ---------------- 
            function Digits(s)
         
                s = tostring(j  * 5)
                
                return s
            end

            X = math.sin((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
            Y = math.cos((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * (-1 * R_Beschr) + Y_c
           txt_add(Digits(s),"font: roboto_regular.ttf; size: 50; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 60, 30)
		   
              
            j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = - 60
y = - 60

txt_add("RPM","font: roboto_bold.ttf; size: 33; color: #999999; halign: center; valign: center",256 + x, 256 + y , 120, 30)

x = - 60
y = 60

txt_add("x100","font: roboto_bold.ttf; size: 33; color: #999999; halign: center; valign: center",256 + x, 256 + y , 120, 30)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------
x = 30
y = 75

img_needle = img_add ("needle.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

function PT_RPM(RPM)
        Alpha = ZWEI_PI/v_max * RPM + OMEGA
        rotate(img_needle, Alpha)
end

---------------------------------------------------------------------------------

x = 28
y = x

img_add("glass.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

u = 8
v = 5
w = 15

img_add("bezel4.png",0 + u ,0 + v ,512 - w,512 - w)

-- x = 10
-- y = x

-- img_add("bezel.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

fs2020_variable_subscribe("GENERAL ENG RPM:1", "rpm", PT_RPM)
