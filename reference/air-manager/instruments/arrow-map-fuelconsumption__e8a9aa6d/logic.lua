--------------------------------------------------------------MANIFOLD PRESSURE------------------------------------------------------------------------------------

img_add_fullscreen("BG.png")

---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 256                   --> Y-Koordinate des Kreismittelpunktes
x       = -30                   --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y       = -15                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
R_Skale12  = 180                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 + 4       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12      --> Radius der Stopstrich
R_BG      = R_Skale12 + 30      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 15      --> Radius des GREEN ARCS
R_arc_t   = R_Skale12 + 30
R_Beschr  = R_Skale12 - 20       --> Radius der Skale

v_min    = 10       --> minimal angezeigte MAP
v_max    = 50       --> maximal angezeigte MAP
v_Delta  = v_max - v_min

v_g_1    = 10        --> Startwert GREEN ARC
v_g_2    = 41       --> Endwert GREEN ARC
MUV      = 5        --> Main-Unit-Value (1. Skale)


N            = var_format(v_Delta/MUV, 0)   --> Anzahl der Werte/Striche im Kreis
ZWEI_PI      = 180            --> Grad-Nutzung der Skale
OMEGA        = - 90          --> Skalendrehung um XY Grad
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/5     --> Skalenabstand 1. und 2. Skale
StrL1       = 25          --> Strichlänge (10er Striche)
StrL2        = 16         --> Strichlänge (5er Striche)
StrL_Stop    = 35

j = 0
s = ""
---------------------------------------------------------------------------
  --------- grüner Bogen -------------------
canvas_add(0, 0, 512, 512, function()
    Alpha_1 = ZWEI_PI/v_Delta * (v_g_1 - v_min) + OMEGA - 90
    Alpha_2 = ZWEI_PI/v_Delta * (v_g_2 - v_min) + OMEGA - 90
   _arc(X_c, Y_c, Alpha_1, Alpha_2,R_arc_g)
  _stroke("green", 10)

  ---------roter Stopstrich  ---------------
    Alpha_3 = ZWEI_PI/v_Delta * (v_g_2 - v_min + 0.25) + OMEGA
  X = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * R_Stop) + X_c
  Y = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * R_Stop) + Y_c
  d = math.sin((Alpha_3) / 360 * 2 * math.pi) * ( 1 * (R_Stop + StrL_Stop)) + X_c
  p = math.cos((Alpha_3) / 360 * 2 * math.pi) * (-1 * (R_Stop + StrL_Stop)) + Y_c   
                
  _move_to(X, Y)
  _line_to(d, p)
  _stroke("red", 5)
  
  -----------weiße Dreiecke-----------------

   x2 = math.sin((ZWEI_PI/v_Delta * (-0.2) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_arc_t) + X_c
   y2 = math.cos((ZWEI_PI/v_Delta * (-0.2) + OMEGA) / 360 * 2 * math.pi) * (-1 * R_arc_t) + Y_c
   x3 = math.sin((ZWEI_PI/v_Delta * 1 + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_arc_t) + X_c
   y3 = math.cos((ZWEI_PI/v_Delta * 1 + OMEGA) / 360 * 2 * math.pi) * (-1 * R_arc_t) + Y_c
   _triangle(246, 256, x2, y2, x3, y3)
   _fill("white")
   
   -- ZWEI_PI/v_Delta * MAP + OMEGA
         
   x2 = math.sin((ZWEI_PI/v_Delta * (50.2) + OMEGA - 2 * PHI1) / 360 * 2 * math.pi) * ( 1 * R_arc_t) + X_c
   y2 = math.cos((ZWEI_PI/v_Delta * (50.2) + OMEGA - 2 * PHI1) / 360 * 2 * math.pi) * (-1 * R_arc_t) + Y_c
   x3 = math.sin((ZWEI_PI/v_Delta * 49 + OMEGA - 2 * PHI1) / 360 * 2 * math.pi) * ( 1 * R_arc_t) + X_c
   y3 = math.cos((ZWEI_PI/v_Delta * 49 + OMEGA - 2 * PHI1) / 360 * 2 * math.pi) * (-1 * R_arc_t) + Y_c
   _triangle(266, 256, x2, y2, x3, y3)
   _fill("white")
      
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
                 if (j + 2)  * 5 == v_max then
                     s = ""
                 elseif (j + 2)  * 5 == v_min then
                     s = ""
                 elseif (j + 2)  * 5 < v_max and (j + 2)  * 5 > v_min then
                     s = tostring((j + 2)  * 5)  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                 end
                 return s
            end

            X = math.sin((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
            Y = math.cos((PHI1 * j + OMEGA) / 360 * 2 * math.pi) * (-1 * R_Beschr) + Y_c
          
           txt_add(Digits(s),"font: roboto_regular.ttf; size: 30; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 60, 30)
           
            j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = - 100
y = - 140
txt_add("MANIFOLD","font: roboto_bold.ttf; size: 30; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 50)
x = - 100
y = - 120
txt_add("PRESSURE","font: roboto_bold.ttf; size: 30; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 50)
x = - 100
y = - 60
txt_add("INCHES OF MERCURY","font: roboto_bold.ttf; size: 20; color: #999999; halign: center; valign: center",256 + x, 256 + y , 200, 30)
x = - 100
y = - 45
txt_add("ABSOLUTE","font: roboto_bold.ttf; size: 20; color: #999999; halign: center; valign: center",256 + x, 256 + y , 200, 30)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------
x = 30
y = 75

img_needle_MAP = img_add ("needle_MAP.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

function PT_MAP(MAP)
        MAP = var_cap(MAP,0,45)
        if MAP < 11 then
        MAP = 11
        else
        MAP = MAP
        end

        Alpha = ZWEI_PI/v_Delta * MAP + OMEGA
        rotate(img_needle_MAP, Alpha - 2 * PHI1) ----- wegen der Verschiebung um Zwei Hauptintervalle
end

fs2020_variable_subscribe("ENG MANIFOLD PRESSURE:1", "inHG", PT_MAP)


--------------------------------------------------------------FUEL Consumption------------------------------------------------------------------------------------

---------------------Parameter---------------------------- 
X_c_FF     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c_FF     = 256                   --> Y-Koordinate des Kreismittelpunktes
x_FF       = - 30                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y_FF     = - 17                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
x_FF_24       = - 25                   --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG des Wertes 24
y_FF_24     =  - 7                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG des Wertes 24
x_FF_PSI       = - 35                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG für den Grenzdruck 19 PSI
y_FF_PSI     = -23                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG für den Grenzdruck 19 PSI
R_Skale12_FF  = 165                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3_FF  = R_Skale12_FF + 14       --> Radius der Skale 3 (5er Striche)
R_Stop_FF    = R_Skale12_FF + 14      --> Radius der Stopstrich
R_BG_FF      = R_Skale12_FF + 45      --> Radius des Hintergrundes
R_arc_g_FF   = R_Skale12_FF + 32     --> Radius des GREEN ARCS
R_arc_g_100_FF   = R_Skale12_FF + 22     --> Radius des GREEN ARCS 100 Prozent
R_arc_g_75_FF   = R_Skale12_FF + 4.4     --> Radius des GREEN ARCS 75 Prozent
R_arc_g_65_FF   = R_Skale12_FF + 14.4     --> Radius des GREEN ARCS 65 Prozent
R_arc_g_55_FF   = R_Skale12_FF + 24.4     --> Radius des GREEN ARCS 55 Prozent

R_Beschr_FF  = R_Skale12_FF - 10        --> Radius der Beschriftung

v_min_FF    = 0       --> minimal angezeigte MAP
v_max_FF    = 25       --> maximal angezeigte MAP
v_Delta_FF  = v_max_FF - v_min_FF

v_g_1_FF    = 0        --> Startwert GREEN ARC
v_g_2_FF    = 24       --> Endwert GREEN ARC 100 Prozent
v_g_1_100_FF    = 21.5        --> Startwert GREEN ARC 100 Prozent
v_g_2_100_FF    = 24       --> Endwert GREEN 100 Prozent
v_g_1_75_FF    = 10.8        --> Startwert GREEN ARC 75 Prozent
v_g_2_75_FF    = 15       --> Endwert GREEN 75 Prozent
v_g_1_65_FF    = 9.3        --> Startwert GREEN ARC 65 Prozent
v_g_2_65_FF    = 13.1       --> Endwert GREEN 65 Prozent
v_g_1_55_FF    = 8        --> Startwert GREEN ARC 55 Prozent
v_g_2_55_FF    = 11       --> Endwert GREEN 55 Prozent
MUV_FF      = 5        --> Main-Unit-Value (1. Skale)


N_FF            = var_format(v_Delta_FF/MUV_FF, 0)   --> Anzahl der Werte/Striche im Kreis
OMEGA_FF        = 100          --> Skalendrehung um XY Grad )( O Grad ist im Norden der Anzeige)
h               = 1.8       --> Stauchung der Skalierung (Exponent)
ZWEI_PI_FF_nichtnormiert = 165 --> Grad-Nutzung der Skale
ZWEI_PI_FF      = (ZWEI_PI_FF_nichtnormiert)^(1/h)   --> Grad-Nutzung der Skale
PHI1_FF         = ZWEI_PI_FF/N_FF   --> Skalenabstand 1. und 2. Skale
PHI2_FF         = PHI1_FF/5     --> Skalenabstand 1. und 2. Skale
StrL1_FF       = 40         --> Strichlänge (10er Striche)
StrL2_FF        = 32         --> Strichlänge (5er Striche)
StrL_Stop_FF    = 25

j_FF = 0
s_FF = ""
---------------------------------------------------------------------------
  --------- grüner Bogen -------------------
canvas_add(0, 0, 512, 512, function()
    Alpha_1_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_1_FF - v_min_FF))^(h) + OMEGA_FF - 90
    Alpha_2_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_2_FF - v_min_FF))^(h) + OMEGA_FF - 90
    print(v_g_1_FF, Alpha_1_FF, v_g_2_FF, Alpha_2_FF)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_FF)
  _stroke("green", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_FF-4)
  _stroke("white", 1) 


  ---------roter Stopstrich  ---------------
  Alpha_3_FF = Alpha_2_FF + 90
  X_FF = math.sin((Alpha_3_FF + 1) / 360 * 2 * math.pi) * ( 1 * R_Stop_FF) + X_c_FF
  Y_FF = math.cos((Alpha_3_FF + 1) / 360 * 2 * math.pi) * (-1 * R_Stop_FF) + Y_c_FF
  d_FF = math.sin((Alpha_3_FF + 1) / 360 * 2 * math.pi) * ( 1 * (R_Stop_FF + StrL_Stop_FF)) + X_c_FF
  p_FF = math.cos((Alpha_3_FF + 1) / 360 * 2 * math.pi) * (-1 * (R_Stop_FF + StrL_Stop_FF)) + Y_c_FF   
                
  _move_to(X_FF, Y_FF)
  _line_to(d_FF, p_FF)
  _stroke("red", 6)  
   
  PSI = txt_add("19.0 PSI","font: roboto_bold.ttf; size: 12; color: white; halign: center; valign: center",X_FF + x_FF_PSI ,Y_FF + y_FF_PSI , 100, 30)
  rotate(PSI, Alpha_3_FF + 1 + 90)

    --------- grüner Bogen 100 Prozent -------------------
    Alpha_1_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_1_100_FF - v_min_FF))^(h) + OMEGA_FF - 90
    Alpha_2_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_2_100_FF - v_min_FF))^(h) + OMEGA_FF - 90
    print(v_g_1_100_FF, Alpha_1_FF, v_g_2_100_FF, Alpha_2_FF)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_100_FF)
   _stroke("green", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_100_FF - 4)
   _stroke("white", 1)
      _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_1_FF + 0.3 ,R_arc_g_100_FF)
   _stroke("white", 10)
   
       --------- grüner Bogen 75 Prozent -------------------
    Alpha_1_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_1_75_FF - v_min_FF))^(h) + OMEGA_FF - 90
    Alpha_2_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_2_75_FF - v_min_FF))^(h) + OMEGA_FF - 90
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_75_FF)
   _stroke("green", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_75_FF - 4)
   _stroke("white", 1)
      _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_1_FF + 0.3 ,R_arc_g_75_FF)
   _stroke("white", 10)   
   
       --------- grüner Bogen 65 Prozent -------------------
    Alpha_2_75_FF = Alpha_2_FF  
    Alpha_1_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_1_65_FF - v_min_FF))^(h) + OMEGA_FF - 90
    Alpha_2_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_2_65_FF - v_min_FF))^(h) + OMEGA_FF - 90
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_65_FF)
   _stroke("green", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_75_FF,R_arc_g_65_FF - 4)
   _stroke("white", 1)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_1_FF + 0.3, R_arc_g_65_FF)
   _stroke("white", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_2_FF - 0.3, Alpha_2_FF, R_arc_g_65_FF)
   _stroke("white", 10)
   
      --------- grüner Bogen 55 Prozent -------------------
    Alpha_2_65_FF = Alpha_2_FF  
    Alpha_1_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_1_55_FF - v_min_FF))^(h) + OMEGA_FF - 90
    Alpha_2_FF = (ZWEI_PI_FF/v_Delta_FF * (v_g_2_55_FF - v_min_FF))^(h) + OMEGA_FF - 90
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_FF,R_arc_g_55_FF)
   _stroke("green", 10)
   _arc(X_c_FF, Y_c_FF, Alpha_1_FF, Alpha_2_65_FF,R_arc_g_55_FF - 4)
   _stroke("white", 1)
   _arc(X_c_FF, Y_c_FF, Alpha_2_FF - 0.3, Alpha_2_FF, R_arc_g_55_FF)
   _stroke("white", 10)
              
end)

  

---------------------------------------------------------------------------
    N_FF = tonumber(N_FF)
    while(j_FF <= N_FF ) -- 0..11 (Bei 12 Werten)
        do
-----------------   1. Skale   ----------------
            if j_FF == 0  then
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_FF = math.sin(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * R_Skale12_FF) + X_c_FF
					Y_FF = math.cos(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * R_Skale12_FF) + Y_c_FF
					d_FF = math.sin(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * (R_Skale12_FF + StrL1_FF)) + X_c_FF
					p_FF = math.cos(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * (R_Skale12_FF + StrL1_FF)) + Y_c_FF   
                
						Stroke = canvas_add(0, 0, 512, 512, function()
							_move_to(X_FF, Y_FF)
							_line_to(d_FF, p_FF)
							_stroke("white", 1)
						end)
						
            elseif j_FF == 5  then   ------------------------------------------------------------------------------------------------------------------------> ONLY FOR PIPER ARROW III (TURBO) -- JUST FLIGHT
            
            				
	    elseif j_FF == 1  then  -----------------------------Weglassen des 5er Hauptstrichs und der Sub-Striche für 6 und 7 GPH 
	            k_FF = 3
                    while(k_FF <=  4) -- Anzahl der Zwischenstriche z.B.: 1..4 (Strichwert = 100; Bei 4 kurzen Strichen, der 5. ist bereits ein langer Strich)
                    do
                        if j_FF == N_FF then
                        
                        else
                             ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                            X_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * R_Skale3_FF) + X_c_FF
                            Y_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * R_Skale3_FF) + Y_c_FF
                            d_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * (R_Skale3_FF + StrL2_FF)) + X_c_FF
                            p_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * (R_Skale3_FF + StrL2_FF)) + Y_c_FF
                            
                            Stroke = canvas_add(0, 0, 512, 512, function()
                                    _move_to(X_FF, Y_FF)
                                    _line_to(d_FF, p_FF)
                                    _stroke("white", 1)
                            end)
                        end
     
                           k_FF = k_FF + 1
                    end			
            else                  
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_FF = math.sin(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * R_Skale12_FF) + X_c_FF
					Y_FF = math.cos(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * R_Skale12_FF) + Y_c_FF
					d_FF = math.sin(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * (R_Skale12_FF + StrL1_FF)) + X_c_FF
					p_FF = math.cos(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * (R_Skale12_FF + StrL1_FF)) + Y_c_FF   
                
						Stroke = canvas_add(0, 0, 512, 512, function()
							_move_to(X_FF, Y_FF)
							_line_to(d_FF, p_FF)
							_stroke("white", 5)
						end)

                    -----------------   Subskale-Skale   ----------------   
                                     
                    k_FF = 1
                    while(k_FF <=  4) -- Anzahl der Zwischenstriche z.B.: 1..4 (Strichwert = 100; Bei 4 kurzen Strichen, der 5. ist bereits ein langer Strich)
                    do
                        if j_FF == N_FF then
                        
                        elseif j_FF == 4 and k_FF == 4 then ---------------------------------------------------------------------------------------------------------> ONLY FOR PIPER ARROW III (TURBO) -- JUST FLIGHT
                                                    ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                            X_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * R_Skale12_FF) + X_c_FF
                            Y_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * R_Skale12_FF) + Y_c_FF
                            d_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * (R_Skale12_FF + StrL1_FF)) + X_c_FF
                            p_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * (R_Skale12_FF + StrL1_FF)) + Y_c_FF
                            
                            Stroke = canvas_add(0, 0, 512, 512, function()
                                    _move_to(X_FF, Y_FF)
                                    _line_to(d_FF, p_FF)
                                    _stroke("white", 5)
                                    end)
                                    
                                function Digits(s_FF)                
                                s_FF = tostring("24")  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                return s_FF
                                end                                            
                                X_FF = math.sin(((PHI1_FF * j_FF + PHI2_FF * k_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * R_Beschr_FF) + X_c_FF
                                Y_FF = math.cos(((PHI1_FF * j_FF + PHI2_FF * k_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * R_Beschr_FF) + Y_c_FF
                               ------ print(j, N, s, Digits(s))
                                
                               txt_add(Digits(s_FF),"font: roboto_regular.ttf; size: 25; color: #ffffff; halign: center; valign: center",X_FF + x_FF_24 ,Y_FF + y_FF_24 , 60, 30)
                               
                        else
                            ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                            X_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * R_Skale3_FF) + X_c_FF
                            Y_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * R_Skale3_FF) + Y_c_FF
                            d_FF = math.sin(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * ( 1 * (R_Skale3_FF + StrL2_FF)) + X_c_FF
                            p_FF = math.cos(((PHI2_FF * k_FF + PHI1_FF * j_FF)^(h) + OMEGA_FF)/ 360 * 2 * math.pi) * (-1 * (R_Skale3_FF + StrL2_FF)) + Y_c_FF
                            
                            Stroke = canvas_add(0, 0, 512, 512, function()
                                    _move_to(X_FF, Y_FF)
                                    _line_to(d_FF, p_FF)
                                    _stroke("white", 2)
                                    end)
                        end
     
                                k_FF = k_FF + 1
                    end
                    

-----------------  Beschriftung   ---------------- 
                            if j_FF == 1  then
                            
                            else
                                function Digits(s_FF)                
                                         s = tostring((j_FF )  * 5)  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X_FF = math.sin(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * ( 1 * R_Beschr_FF) + X_c_FF
                                Y_FF = math.cos(((PHI1_FF * j_FF)^(h) + OMEGA_FF) / 360 * 2 * math.pi) * (-1 * R_Beschr_FF) + Y_c_FF
                               ------ print(j, N, s, Digits(s))
                               txt_add(Digits(s),"font: roboto_regular.ttf; size: 25; color: #ffffff; halign: center; valign: center",X_FF + x_FF ,Y_FF + y_FF , 60, 30)
                            end
                           
            end
			
			j_FF = j_FF + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = - 100
y = 30
txt_add("GALLON/HOUR","font: roboto_bold.ttf; size: 30; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 50)
-- x = - 100
-- y = - 120
-- txt_add("PRESSURE","font: roboto_bold.ttf; size: 30; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 200, 50)
x = - 100
y = 80
txt_add("FUEL FLOW","font: roboto_bold.ttf; size: 20; color: #999999; halign: center; valign: center",256 + x, 256 + y , 200, 30)
-- x = - 100
-- y = - 45
-- txt_add("ABSOLUTE","font: roboto_bold.ttf; size: 20; color: #999999; halign: center; valign: center",256 + x, 256 + y , 200, 30)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------
x = 30
y = 75

img_needle_FF = img_add ("needle_FF.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

function PT_FF(FF)
        FF = var_cap(FF,0,24)
        Alpha_FF = (ZWEI_PI_FF/v_Delta_FF * FF)^(h) + OMEGA_FF
        rotate(img_needle_FF, Alpha_FF)
        print(Alpha_FF + 20)
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

fs2020_variable_subscribe("ENG FUEL FLOW GPH:1", "Gallons per hour", PT_FF)
