---------------------Parameter---------------------------- 
X_c     = 256                   --> X-Koordinate des Kreismittelpunktes
Y_c     = 256                   --> Y-Koordinate des Kreismittelpunktes
x       = -23                   --> Verschiebung X-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
y       = -15                   --> Verschiebung y-Koordinate des Kreismittelpunktes der BESCHRIFTUNG
R_Skale12  = 170                --> Radius der Skale 1 und 2 (10er Striche)
R_Skale3  = R_Skale12 + 6       --> Radius der Skale 3 (5er Striche)
R_BG      = R_Skale12 + 30      --> Radius des Hintergrundes

R_Ring1   = R_BG + 4      --> Radius des 1. Rings
R_Ring2   = R_Ring1 + 4      --> Radius des 2. Rings
R_Ring3   = R_Ring2 + 2      --> Radius des 3. Rings

R_arc_gy   = R_Skale12 + 25     --> Radius des GREEN-YELLEOW ARCS
R_arc_w   = R_Skale12 + 15      --> Radius des WHITE ARCS
R_arc_b   = R_Skale12 + 7       --> Radius des BLUE ARCS
R_arc_dg   = R_Skale12 + 2      --> Radius des DARK GREEN ARCS
R_arc_db   = R_Skale12 - 2      --> Radius des DARK BLUE ARCS
R_Beschr  = R_Skale12 -30       --> Radius der Skale

v_max    = 190       --> maximal angezeigte Geschwindigkeit
v_g_1    = 65        --> Startwert GREEN ARC
v_g_2    = 100       --> Endwert GREEN ARC
v_y_1    = v_g_2     --> Startwert YELLOW ARC
v_y_2    = 183       --> Endwert YELLOW ARC
v_w_1    = 56        --> Startwert WHITE ARC --> Flaps
v_w_2    = 103       --> Endwert WHITE ARC ---> Max Flaps Extended Speed
v_rot_1    = 70       --> Startwert DARK BLUE ARC --> V_rotate min
v_rot_2    = 77       --> Endwert DARK BLUE ARC ---> V_rotate max
v_dg_1    = 96        --> Startwert DARK GREEN ARC --> Max. Maneuver Speed (e.g. 1893 lbs --> Piper Arrow III)
v_dg_2    = 119       --> Endwert DARK GEEN ARC ---> Max. Maneuver Speed (e.g. 2900 lbs --> Piper Arrow III)



v_NES    = v_y_2     --> nicht zu überschreitende Geschwindigkeit
v_Stall  = 56        --> nicht zu unterschreitende Geschwindigkeit
v_b_1    = 78        --> Best Angle Of Climb
v_b_2    = 96        --> Best Rate Of Climb
v_LE     = 129       --> Max. Gear Extended Speed�

N        = var_round(v_max/20,0)   --> Anzahl der Werte/Striche im Kreis
PHI1     = 360/N     --> Skalenabstand 1. und 2. Skale
PHI2     = PHI1/2     --> Skalenabstand 1. und 2. Skale
ROH1     = PHI1/2      --> Phasenverschiebung für 2.Skale
ROH2     = ROH1/2      --> Phasenverschiebung für 2.Skale
StrL1    = 30         --> Strichlänge (10er Striche)
StrL2    = 24         --> Strichlänge (5er Striche)
StrL3    = 30        --> Strichlänge (v_NES)
StrL4    = 20        --> Strichlänge (v_NLE)



local j = 0
local s = ""
---------------------------------------------------------------------------

Ring3 = canvas_add(0, 0, 512, 512, function()
  _circle(X_c, Y_c, R_Ring3)
   -- _stroke("#353535", 10)
  _fill_gradient_linear(X_c - R_Ring3, Y_c - R_Ring3, X_c + R_Ring3, Y_c + R_Ring3, "#0f0f0f", "#878787")
end)

Ring2 = canvas_add(0, 0, 512, 512, function()
  _circle(X_c, Y_c, R_Ring2)
   -- _stroke("#353535", 10)
  _fill_gradient_linear(X_c - R_Ring2, Y_c - R_Ring2, X_c + R_Ring2, Y_c + R_Ring2, "#3e3e3e", "#1b1b1b")
end)

Ring1 = canvas_add(0, 0, 512, 512, function()
  _circle(X_c, Y_c, R_Ring1)
   -- _stroke("#353535", 10)
  _fill_gradient_linear(X_c - R_Ring1, Y_c - R_Ring1, X_c + R_Ring1, Y_c + R_Ring1, "#878787", "#0f0f0f")
end)

Background = canvas_add(0, 0, 512, 512, function()
  _circle(X_c, Y_c, R_BG)
  -- _fill("#0f0f0f")
  _fill_gradient_linear(X_c - R_BG, Y_c - R_BG, X_c + R_BG, Y_c + R_BG, "#000000", "#0f0f0f") -- "#3e3e3e"
end)


arc_green = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_g_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_g_2 - 20) *360)/(20* N) - 90
   _arc(X_c, Y_c, Alpha_1, Alpha_2,R_arc_gy)
  _stroke("green", 10)
end)

arc_darkgreen = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_dg_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_dg_2 - 20) *360)/(20* N) - 90
  _arc(X_c, Y_c,Alpha_1,Alpha_2,R_arc_dg)
  _stroke("#004d00", 36)
  end)

arc_yellow = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_y_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_y_2 - 20) *360)/(20* N) - 90
  _arc(X_c, Y_c,Alpha_1,Alpha_2,R_arc_gy)
  _stroke("yellow", 10)
end)

arc_blue = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_b_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_b_2 - 20) *360)/(20* N) - 90
  _arc(X_c, Y_c,Alpha_1,Alpha_2,R_arc_b)
  _stroke("#7676ff", 7)
end)

arc_darkblue = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_rot_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_rot_2 - 20) *360)/(20* N) - 90
  _arc(X_c, Y_c,Alpha_1,Alpha_2,R_arc_db)
  _stroke("#0000ff", 25)
end)

arc_white = canvas_add(0, 0, 512, 512, function()
    Alpha_1= ((v_w_1 - 20) *360)/(20* N) - 90 
    Alpha_2= ((v_w_2 - 20) *360)/(20* N) - 90
  _arc(X_c, Y_c,Alpha_1,Alpha_2,R_arc_w)
  _stroke("white", 12)
end)

---------------------------------------------------------------------------

    while(j <= N - 1) -- 0..11 (Bei 12 Werten)
        do
-----------------   1. Skale   ----------------
                 -- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                X = math.sin(PHI1 * j / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos(PHI1 * j / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin(PHI1 * j / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL1)) + X_c
                p = math.cos(PHI1 * j / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL1)) + Y_c   
                
                    Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("white", 3)
                    end)
                    
-----------------   2. Skale   ----------------
            if j == 0 or j == N - 1 then
            
            else
                 -- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                X = math.sin((PHI1 * j + ROH1)/360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos((PHI1 * j + ROH1)/360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin((PHI1 * j + ROH1)/360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL1)) + X_c
                p = math.cos((PHI1 * j + ROH1)/360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL1)) + Y_c
                         
                    Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("white", 3)
                    end)
            end
-----------------  Beschriftung   ---------------- 
            function Digits(s)
                if j == 0 then
                s = tostring(0)
                else
                s = tostring((j + 1) * 20,0)
                end
                return s
            end

            X = math.sin(PHI1 * j / 360 * 2 * math.pi) * ( 1 * R_Beschr) + X_c
            Y = math.cos(PHI1 * j / 360 * 2 * math.pi) * (-1 * R_Beschr) + Y_c
           txt_add(Digits(s),"font: arimo_regular.ttf; size: 30; color: white; halign: center; valign: center",X + x ,Y + y , 50, 30)
              
            j = j + 1
    end
--------------------------------------------------    
        j = 0
        while(j <= (2 * N) - 1) -- 0..23 (Bei 12 Werten)
        do
-----------------   3. Skale   ----------------
            if j == 0 or j == 1 or j == (2 * N) - 2 or j == (2 * N) - 1 then
            
            else
                 -- SIN/COS von jedem Winkel an dem ein Strich erscheinen soll (abhänig von der Gewünschten Anzahl an Strichen )   
                X = math.sin((PHI2 * j + ROH2)/360 * 2 * math.pi) * ( 1 * R_Skale3) + X_c
                Y = math.cos((PHI2 * j + ROH2)/360 * 2 * math.pi) * (-1 * R_Skale3) + Y_c
                d = math.sin((PHI2 * j + ROH2)/360 * 2 * math.pi) * ( 1 * (R_Skale3 + StrL2)) + X_c
                p = math.cos((PHI2 * j + ROH2)/360 * 2 * math.pi) * (-1 * (R_Skale3 + StrL2)) + Y_c
                
                Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("white", 1)
                end)
            end       
                    j = j + 1
        end
------------------------------------------------------------------------------
--------------- Never-Exceed-Speed ---------------
                if v_NES < 40 then
                Alpha = ((v_NES) *360)/(20* N) / 2  -- "/2" --> Doppelter Skalenabstand
                elseif v_NES >= 40 then
                Alpha = ((v_NES - 20) *360)/(20* N)            
                end
                
                X = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL3)) + X_c
                p = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL3)) + Y_c
                
                Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("red", 5)
                end)
                
--------------- Never-Deceed-Speed ---------------
                if v_Stall < 40 then
                Alpha = ((v_Stall) *360)/(20* N) / 2  -- "/2" --> Doppelter Skalenabstand
                elseif v_NES >= 40 then
                Alpha = ((v_Stall - 20) *360)/(20* N)            
                end
                
                X = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL3)) + X_c
                p = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL3)) + Y_c
                
                Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("red", 5)
                end)
                
--------------- Max. Gear Extended Speed) ---------------
                if v_LE < 40 then
                Alpha = ((v_LE) *360)/(20* N) / 2  -- "/2" --> Doppelter Skalenabstand
                elseif v_NES >= 40 then
                Alpha = ((v_LE - 20) *360)/(20* N)            
                end
                
                X = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * R_Skale12) + X_c
                Y = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * R_Skale12) + Y_c
                d = math.sin((Alpha) / 360 * 2 * math.pi) * ( 1 * (R_Skale12 + StrL4)) + X_c
                p = math.cos((Alpha) / 360 * 2 * math.pi) * (-1 * (R_Skale12 + StrL4)) + Y_c
                
                Stroke = canvas_add(0, 0, 512, 512, function()
                        _move_to(X, Y)
                        _line_to(d, p)
                        _stroke("#ff7676", 5)
                end)



------------------------------------------------------------------------------
-- Eingabe hilfe zur Verzerrung der Nadel
x = 30
y = 0

img_needle = img_add ("needle.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

function PT_airspeed(airspeed)
    if airspeed < 40 then
        Alpha = ((airspeed) *360)/(20* N) / 2  -- "/2" --> Doppelter Skalenabstand
        rotate(img_needle, Alpha)
    elseif airspeed >= 40 then
        Alpha = ((airspeed - 20) *360)/(20* N)
        rotate(img_needle, Alpha)
    end
end
x = 41
y = x

-- img_add("glass.png",0 + x/2 ,0 + y/2 ,512 - x,512 - y)

fs2020_variable_subscribe("AIRSPEED INDICATED", "knots", PT_airspeed)
