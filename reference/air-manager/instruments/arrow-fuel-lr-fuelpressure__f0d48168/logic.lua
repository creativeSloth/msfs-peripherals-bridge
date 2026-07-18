
--------------------------------------------------------------LEFT FUEL Capacity------------------------------------------------------------------------------------
-- ------Hintergrund-------------

img_add("BG.png",0 , 0, 512, 256)

---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 238                   --> Y-Koordinate des Kreismittelpunktes
x       = - 50                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y     = - 50                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG

X_needle = 256                --> X-Koordinate des Rotationsmittelpunktes der Nadel
Y_needle = 400                --> Y-Koordinate des Rotationsmittelpunktes der Nadel
x_needle = 50               --> Eingabehilfe zur Verzerrung der Nadel ----------------
y_needle = 750              --> Eingabehilfe zur Verzerrung der Nadel ----------------

R_Skale12  = 220                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 - 0       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12 + 0      --> Radius der Stopstrich
R_BG      = R_Skale12 + 45      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 40     --> Radius des GREEN ARCS
R_arc_w   = R_Skale12 + 2     --> Radius des GREEN ARCS

R_Beschr  = R_Skale12 - 15        --> Radius der Beschriftung

LEFT_FUEL_min    = 0       --> minimal angezeigte Wert
LEFT_FUEL_max    = 38.5       --> maximal angezeigte Wert
LEFT_FUEL_Delta  = LEFT_FUEL_max - LEFT_FUEL_min

MUV      = 10        --> Main-Unit-Value (1. Skale)

N            = LEFT_FUEL_Delta/MUV   --> Anzahl der Werte/Striche im Kreis
OMEGA        =  -50         --> Skalendrehung um XY Grad )( O Grad ist im Norden der Anzeige)
h               = 1       --> Stauchung der Skalierung (Exponent)
ZWEI_PI_nichtnormiert = 100 --> Grad-Nutzung der Skale
ZWEI_PI      = (ZWEI_PI_nichtnormiert)^(1/h)   --> Grad-Nutzung der Skale
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/4     --> Skalenabstand 1. und 2. Skale
StrD       = 25         --> Strichdicke (Haupt-Skala Striche)
StrL1        = 50      --> "Winkel" der Striche (Haupt-Skala Striche)
StrL11       = 60        --> Strichlänge (Haupt-Skala Striche)
StrL_Stop    = 49.5

j = 0
s = ""
---------------------------------------------------------------------------
local settings0 = {}
    N = tonumber(N)
    while(j <= N )
        do
-----------------   1. Skale   ----------------
                
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
					X_1_1 = X_1 - StrD/2
					X_1_2 = X_1 + StrD/2
					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
					X_2_1 = X_2 - StrD/2
					X_2_2 = X_2 + StrD/2
					Y_1 = 102
					Y_2 = Y_1 - StrL11  
                
						Stroke = canvas_add(0, 0, 512, 512, function()
							_move_to(X_1_1, Y_1)
							_line_to(X_1_2, Y_1)
							_line_to(X_2_2, Y_2)
							_line_to(X_2_1, Y_2)
							_line_to(X_1_1, Y_1)
							
							_fill("white")
						end)

                    

-----------------  Beschriftung   ---------------- 

                                function Digits(s)                
                                         s = tostring(var_format((j * MUV + LEFT_FUEL_min),0))  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                Y = 102
                              
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 80, 150)
----------------- Rotationswerte für Nadel ----------------------------
                               Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
                               table.insert (settings0, { j * MUV, -Gamma })
                       
--------------------------- Abschluss-Strich und "F"	


        					
        					if j > N-1 then
        					j = N    
        					
                				X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
        					X_1_1 = X_1 - StrD/2
        					X_1_2 = X_1 + StrD/2
        					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
        					X_2_1 = X_2 - StrD/2
        					X_2_2 = X_2 + StrD/2
        					Y_1 = 102
        					Y_2 = Y_1 - StrL11  
                        
        						Stroke = canvas_add(0, 0, 512, 512, function()
        							_move_to(X_1_1, Y_1)
        							_line_to(X_1_2, Y_1)
        							_line_to(X_2_2, Y_2)
        							_line_to(X_2_1, Y_2)
        							_line_to(X_1_1, Y_1)
        							
        							_fill("white")
        					        end)
        					----------------- Rotationswerte für Nadel ----------------------------
        					Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
        					table.insert (settings0,{ N * MUV, - Gamma })
        					 
                        			-----------------  Beschriftung   ---------------- 
                
                                                function Digits(s)                
                                                         s = "F"  
                                                         return s
                                                end
                                                                                            
                                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                                Y = 102
                                                x_offset = 15
                                               ------ print(j, N, s, Digits(s))
                                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x + x_offset ,Y + y , 80, 150)
        					end
                           
            			
			j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = -256
y = -20
txt_add("FUEL U.S. GALS","font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",256 + x, 128 + y , 512, 150)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------

img_needle1 = img_add("needle.png",X_needle - x_needle/2 , Y_needle - y_needle/2 , x_needle, y_needle)
viewport_rect(img_needle1, 0, -216, 512, 600)
img_glass1 = img_add("glass.png", -256 , -256 , 1024, 1028)
viewport_rect(img_glass1, 0, 0, 512, 256)

fs2020_variable_subscribe("FUEL LEFT QUANTITY", "Gallons",
                          "ELECTRICAL MAIN BUS VOLTAGE", "Volts", function (fuel_left, bus_volts)

                            fuel_left = var_cap(fuel_left, LEFT_FUEL_min, LEFT_FUEL_max)

                            if bus_volts < 8 then
                                fuel_left = 0
                            end
                            rotate(img_needle1, interpolate_linear(settings0, fuel_left), "LINEAR", 0.02)
                        end)


--------------------------------------------------------------Fuel Pressure------------------------------------------------------------------------------------
-- ------Hintergrund-------------

img_add("BG.png",512 , 0, 512, 256)

---------------------Parameter---------------------------- 
X_c     = 768                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 238                   --> Y-Koordinate des Kreismittelpunktes
x       = - 50                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y     = - 50                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG

X_needle = 768                --> X-Koordinate des Rotationsmittelpunktes der Nadel
Y_needle = 400                --> Y-Koordinate des Rotationsmittelpunktes der Nadel
x_needle = 50               --> Eingabehilfe zur Verzerrung der Nadel ----------------
y_needle = 750              --> Eingabehilfe zur Verzerrung der Nadel ----------------

R_Skale12  = 220                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 - 0       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12 + 0      --> Radius der Stopstrich
R_BG      = R_Skale12 + 45      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 40     --> Radius des GREEN ARCS
R_arc_w   = R_Skale12 + 2     --> Radius des GREEN ARCS

R_Beschr  = R_Skale12 - 15        --> Radius der Beschriftung

PRESS_FUEL_min    = 0       --> minimal angezeigte Wert
PRESS_FUEL_max    = 50       --> maximal angezeigte Wert
PRESS_FUEL_Delta  = PRESS_FUEL_max - PRESS_FUEL_min

--rote Striche
FuPr_rStr_1       = 14        --> Fuel Pressure für ersten roten Strich
x_rStr1_kor       = 1.5       --> Korrekturverschiebung des roten Strichs
FuPr_rStr_2       = 38        --> Fuel Pressure für ersten roten Strich
x_rStr2_kor       = -1.5       --> Korrekturverschiebung des roten Strichs

MUV      = 50        --> Main-Unit-Value (1. Skale)

N            = PRESS_FUEL_Delta/MUV   --> Anzahl der Werte/Striche im Kreis
OMEGA        =  -50         --> Skalendrehung um XY Grad )( O Grad ist im Norden der Anzeige)
h               = 1       --> Stauchung der Skalierung (Exponent)
ZWEI_PI_nichtnormiert = 100 --> Grad-Nutzung der Skale
ZWEI_PI      = (ZWEI_PI_nichtnormiert)^(1/h)   --> Grad-Nutzung der Skale
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/4     --> Skalenabstand 1. und 2. Skale
StrD       = 25         --> Strichdicke (Haupt-Skala Striche)
StrD_rot   = 10        --> Strichdicke (rote Striche)
StrL1        = 50       --> "Winkel" der Striche (Haupt-Skala Striche)
StrL1_rot        = 35       --> "Winkel" der Striche (Haupt-Skala Striche)
StrL11       = 60        --> Strichlänge (Haupt-Skala Striche)
StrL11_rot   = 40        --> Strichlänge (rote Striche)
StrL_Stop    = 49.5


j = 0
s = ""
---------------------------------------------------------------------------
local settings1 = {}
    N = tonumber(N)
    while(j <= N )
        do
-----------------   1. Skale   ----------------
                
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
					X_1_1 = X_1 - StrD/2
					X_1_2 = X_1 + StrD/2
					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
					X_2_1 = X_2 - StrD/2
					X_2_2 = X_2 + StrD/2
					Y_1 = 102
					Y_2 = Y_1 - StrL11
					
						Stroke = canvas_add(0, 0, 1024, 512, function()
							_move_to(X_1_1, Y_1)
							_line_to(X_1_2, Y_1)
							_line_to(X_2_2, Y_2)
							_line_to(X_2_1, Y_2)
							_line_to(X_1_1, Y_1)
							
							_fill("white")
						end)

                    

-----------------  Beschriftung   ---------------- 

                                function Digits(s)                
                                         s = tostring(var_format((j * MUV + PRESS_FUEL_min),0))  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                Y = 102
                              
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 80, 150)
----------------- Rotationswerte für Nadel ----------------------------
                               Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
                               table.insert (settings1, { j * MUV, -Gamma })
                       
--------------------------- Abschluss-Strich und "F"	

--entfernt--
        					
-----------------------------------------------
                           
            			
			j = j + 1
    end


-----------------   rote Skalen-Striche   ----------------
------ 1. roter Strich
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_1 = math.sin(((ZWEI_PI * (FuPr_rStr_1 + x_rStr1_kor)/PRESS_FUEL_max)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
					X_1_1 = X_1 - StrD_rot/2
					X_1_2 = X_1 + StrD_rot/2
					X_2 = math.sin(((ZWEI_PI *(FuPr_rStr_1 + x_rStr1_kor)/PRESS_FUEL_max)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1_rot) + X_c
					X_2_1 = X_2 - StrD_rot/2
					X_2_2 = X_2 + StrD_rot/2
					Y_1 = 85
					Y_2 = Y_1 - StrL11_rot
					-------Übergabe zuKoordinaten für grünen Balken 
					X_3_1 = X_1
					X_3_2 = X_2
					 
						Stroke = canvas_add(0, 0, 1024, 512, function()
							_move_to(X_1_1, Y_1)
							_line_to(X_1_2, Y_1)
							_line_to(X_2_2, Y_2)
							_line_to(X_2_1, Y_2)
							_line_to(X_1_1, Y_1)
							
							_fill("red")
						end)

                    

-----------------  Beschriftung   ---------------- 

                                function Digits(s)                
                                         s = tostring(var_format((FuPr_rStr_1 + PRESS_FUEL_min),0))  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X = math.sin(((ZWEI_PI * (FuPr_rStr_1 + x_rStr1_kor)/PRESS_FUEL_max)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                Y = 102
                              
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 80, 150)
                               
------ 2. roter Strich
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_1 = math.sin(((ZWEI_PI * (FuPr_rStr_2 + x_rStr2_kor)/PRESS_FUEL_max)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
					X_1_1 = X_1 - StrD_rot/2
					X_1_2 = X_1 + StrD_rot/2
					X_2 = math.sin(((ZWEI_PI * (FuPr_rStr_2 + x_rStr2_kor)/PRESS_FUEL_max)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1_rot) + X_c
					X_2_1 = X_2 - StrD_rot/2
					X_2_2 = X_2 + StrD_rot/2
					Y_1 = 85
					Y_2 = Y_1 - StrL11_rot  
					-------Übergabe zuKoordinaten für grünen Balken 
					X_4_1 = X_1
					X_4_2 = X_2
					--------------------------------------------------
						Stroke = canvas_add(0, 0, 1024, 512, function()
							_move_to(X_1_1, Y_1)
							_line_to(X_1_2, Y_1)
							_line_to(X_2_2, Y_2)
							_line_to(X_2_1, Y_2)
							_line_to(X_1_1, Y_1)
							_fill("red")
						end)
						
					        d = 15 --> Verschiebung der X-Koordinaten
                                                trapeze = canvas_add(0, 0, 1024, 512, function()
							_move_to(X_3_1 + d, Y_1)
							_line_to(X_3_2 + d, Y_2)
							_line_to(X_4_2 - d, Y_2)
							_line_to(X_4_1 - d, Y_1)
							_line_to(X_3_1 + d, Y_1)
							_fill("green")
						end)


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = -256
y = -20
txt_add("FUEL  PRESS","font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",768 + x, 128 + y , 512, 150)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------

img_needle2 = img_add("needle.png",X_needle - x_needle/2 , Y_needle - y_needle/2 , x_needle, y_needle)
viewport_rect(img_needle2, 0, -216, 1024, 600)


fs2020_variable_subscribe("GENERAL ENG FUEL PRESSURE:1", "PSI",
                          "ELECTRICAL MAIN BUS VOLTAGE", "Volts", function (fuel_PRESS, bus_volts)

                            fuel_PRESS = var_cap(fuel_PRESS, PRESS_FUEL_min, PRESS_FUEL_max)

                            if bus_volts < 8 then
                                fuel_PRESS = 0
                            end
                            rotate(img_needle2, interpolate_linear(settings1, fuel_PRESS * 1.891891892), "LINEAR", 0.02)
                        end)


img_glass2 = img_add("glass.png", 256 , -256 , 1024, 1028)
viewport_rect(img_glass2, 512, 0, 512, 256)


--------------------------------------------------------------RIGHT FUEL Capacity------------------------------------------------------------------------------------
-- ------Hintergrund-------------

img_add("BG.png",1024 , 0, 512, 256)

---------------------Parameter---------------------------- 
X_c     = 1280                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 238                   --> Y-Koordinate des Kreismittelpunktes
x       = - 50                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y     = - 50                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG

X_needle = 1280                --> X-Koordinate des Rotationsmittelpunktes der Nadel
Y_needle = 400                --> Y-Koordinate des Rotationsmittelpunktes der Nadel
x_needle = 50               --> Eingabehilfe zur Verzerrung der Nadel ----------------
y_needle = 750              --> Eingabehilfe zur Verzerrung der Nadel ----------------

R_Skale12  = 220                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 - 0       --> Radius der Skale 3 (5er Striche)
R_Stop    = R_Skale12 + 0      --> Radius der Stopstrich
R_BG      = R_Skale12 + 45      --> Radius des Hintergrundes
R_arc_g   = R_Skale12 + 40     --> Radius des GREEN ARCS
R_arc_w   = R_Skale12 + 2     --> Radius des GREEN ARCS

R_Beschr  = R_Skale12 - 15        --> Radius der Beschriftung

RIGHT_FUEL_min    = 0       --> minimal angezeigte Wert
RIGHT_FUEL_max    = 38.5       --> maximal angezeigte Wert
RIGHT_FUEL_Delta  = RIGHT_FUEL_max - RIGHT_FUEL_min

MUV      = 10        --> Main-Unit-Value (1. Skale)

N            = RIGHT_FUEL_Delta/MUV   --> Anzahl der Werte/Striche im Kreis
OMEGA        =  -50         --> Skalendrehung um XY Grad )( O Grad ist im Norden der Anzeige)
h               = 1       --> Stauchung der Skalierung (Exponent)
ZWEI_PI_nichtnormiert = 100 --> Grad-Nutzung der Skale
ZWEI_PI      = (ZWEI_PI_nichtnormiert)^(1/h)   --> Grad-Nutzung der Skale
PHI1         = ZWEI_PI/N   --> Skalenabstand 1. und 2. Skale
PHI2         = PHI1/4     --> Skalenabstand 1. und 2. Skale
StrD       = 25         --> Strichdicke (Haupt-Skala Striche)
StrL1        = 50       --> "Winkel" der Striche (Haupt-Skala Striche)
StrL11       = 60        --> Strichlänge (Haupt-Skala Striche)
StrL_Stop    = 49.5

j = 0
s = ""
---------------------------------------------------------------------------
local settings2 = {}
    N = tonumber(N)
    while(j <= N )
        do
-----------------   1. Skale   ----------------
                
                 ---- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
					X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
					X_1_1 = X_1 - StrD/2
					X_1_2 = X_1 + StrD/2
					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
					X_2_1 = X_2 - StrD/2
					X_2_2 = X_2 + StrD/2
					Y_1 = 102
					Y_2 = Y_1 - StrL11  
                
						Stroke = canvas_add(0, 0, 1536, 512, function()
							_move_to(X_1_1, Y_1)
							_line_to(X_1_2, Y_1)
							_line_to(X_2_2, Y_2)
							_line_to(X_2_1, Y_2)
							_line_to(X_1_1, Y_1)
							
							_fill("white")
						end)

                    

-----------------  Beschriftung   ---------------- 

                                function Digits(s)                
                                         s = tostring(var_format((j * MUV + LEFT_FUEL_min),0))  ----------- Verschiebung der Nulllinie um zwei 5er- Intervalle auf die 10
                                         return s
                                end                                            
                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                Y = 102
                              
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 80, 150)
----------------- Rotationswerte für Nadel ----------------------------
                               Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
                               table.insert (settings2, { j * MUV, -Gamma })
                       
--------------------------- Abschluss-Strich und "F"	


        					
        					if j > N-1 then
        					j = N    
        					
                				X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
        					X_1_1 = X_1 - StrD/2
        					X_1_2 = X_1 + StrD/2
        					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
        					X_2_1 = X_2 - StrD/2
        					X_2_2 = X_2 + StrD/2
        					Y_1 = 102
        					Y_2 = Y_1 - StrL11  
                        
        						Stroke = canvas_add(0, 0, 1536, 512, function()
        							_move_to(X_1_1, Y_1)
        							_line_to(X_1_2, Y_1)
        							_line_to(X_2_2, Y_2)
        							_line_to(X_2_1, Y_2)
        							_line_to(X_1_1, Y_1)
        							_fill("white")
        					        end)
        					----------------- Rotationswerte für Nadel ----------------------------
        					Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
        					table.insert (settings2,{ N * MUV, - Gamma })
        					 
                        			-----------------  Beschriftung   ---------------- 
                
                                                function Digits(s)                
                                                         s = "F"  
                                                         return s
                                                end
                                                                                            
                                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                                Y = 102
                                                x_offset = 15
                                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x + x_offset ,Y + y , 80, 150)
        					end
                           
            			
			j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = -256
y = -20
txt_add("FUEL U.S. GALS","font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",1280 + x, 128 + y , 512, 150)


----------------------- Eingabehilfe zur Verzerrung der Nadel -----------------------

img_needle3 = img_add("needle.png",X_needle - x_needle/2 , Y_needle - y_needle/2 , x_needle, y_needle)
viewport_rect(img_needle3, 1024, -216, 512, 600)

fs2020_variable_subscribe("FUEL RIGHT QUANTITY", "Gallons",
                          "ELECTRICAL MAIN BUS VOLTAGE", "Volts", function (fuel_right, bus_volts)

                            fuel_right = var_cap(fuel_right, RIGHT_FUEL_min, RIGHT_FUEL_max)

                            if bus_volts < 8 then
                                fuel_right = 0
                            end
                            rotate(img_needle3, interpolate_linear(settings2, fuel_right), "LINEAR", 0.02)
                        end)
                        
img_glass3 = img_add("glass.png", 768, -256 , 1024, 1028)
viewport_rect(img_glass3, 1024, 0, 512, 256)

---------------------------------------------------------------------------------

-- u = 30
-- v = u

-- img_add("glass.png",0 + u/2 ,0 + v/2 ,512 - u,512 - v)


