-- ------Hintergrund-------------

img_add("BG.png",0 , 128, 512, 256)


--------------------------------------------------------------FUEL Capacity------------------------------------------------------------------------------------

---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 366                   --> Y-Koordinate des Kreismittelpunktes
x       = - 50                  --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y     = - 25                  --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG

X_needle = 256                --> X-Koordinate des Rotationsmittelpunktes der Nadel
Y_needle = 800                --> Y-Koordinate des Rotationsmittelpunktes der Nadel
x_needle = 50               --> Eingabehilfe zur Verzerrung der Nadel ----------------
y_needle = 1300              --> Eingabehilfe zur Verzerrung der Nadel ----------------

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
StrD       = 30         --> Strichdicke (Haupt-Skala Striche)
StrL1        = 50       --> "Winkel" der Striche (Haupt-Skala Striche)
StrL11       = 60        --> Strichlänge (Haupt-Skala Striche)
StrL_Stop    = 49.5

j = 0
s = ""
---------------------------------------------------------------------------
local settings = {}
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
					Y_1 = 230
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
                                Y = 210
                              
                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x ,Y + y , 80, 150)
----------------- Rotationswerte für Nadel ----------------------------
                               Gamma = math.atan((X_needle - X_1)/(Y_needle - Y_1)) *( 360 / (2 * math.pi))
                               table.insert (settings, { j * MUV, -Gamma })
                       
--------------------------- Abschluss-Strich und "F"	


        					
        					if j > N-1 then
        					j = N    
        					
                				X_1 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * R_Skale12 + X_c
        					X_1_1 = X_1 - StrD/2
        					X_1_2 = X_1 + StrD/2
        					X_2 = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * (R_Skale12 + StrL1) + X_c
        					X_2_1 = X_2 - StrD/2
        					X_2_2 = X_2 + StrD/2
        					Y_1 = 230
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
        					table.insert (settings,{ N * MUV, - Gamma })
        					 
                        			-----------------  Beschriftung   ---------------- 
                
                                                function Digits(s)                
                                                         s = "F"  
                                                         return s
                                                end
                                                                                            
                                                X = math.sin(((PHI1 * j)^(h) + OMEGA) / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
                                                Y = 210
                                                x_offset = 15
                                               ------ print(j, N, s, Digits(s))
                                               txt_add(Digits(s),"font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",X + x + x_offset ,Y + y , 80, 150)
        					end
                           
            			
			j = j + 1
    end


-----------------------Tacho-Hintergrundeschriftung-------------------------
x = -256
y = -20
txt_add("FUEL U.S. GALS","font: roboto_bold.ttf; size: 70; color: #ffffff; halign: center; valign: center",256 + x, 256 + y , 512, 150)


----------------------- Eingabehilfe zur Verzerrung der Nadel ----------------

img_needle = img_add("needle.png",X_needle - x_needle/2 , Y_needle - y_needle/2 , x_needle, y_needle)
viewport_rect(img_needle, 0, -216, 512, 600)

img_glass = img_add("glass.png", -256 , -256 , 1024, 1028)
viewport_rect(img_glass, 0, 128, 512, 256)

print (settings)
fs2020_variable_subscribe("FUEL Right QUANTITY", "Gallons",
                          "ELECTRICAL MAIN BUS VOLTAGE", "Volts", function (fuel_left, bus_volts)

                            fuel_left = var_cap(fuel_left, LEFT_FUEL_min, LEFT_FUEL_max)

                            if bus_volts < 8 then
                                fuel_left = 0
                            end
                            rotate(img_needle, interpolate_linear(settings, fuel_left), "LINEAR", 0.02)
                        end)



---------------------------------------------------------------------------------

-- u = 30
-- v = u

-- img_add("glass.png",0 + u/2 ,0 + v/2 ,512 - u,512 - v)


