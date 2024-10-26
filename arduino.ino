#include <Servo.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Stepper.h>

// Stepper motor pin definitions
#define STEPPER_PIN_1 9
#define STEPPER_PIN_2 10
#define STEPPER_PIN_3 11
#define STEPPER_PIN_4 12

// Define the number of steps per revolution for the 28BYJ-48 stepper motor
const int stepsPerRevolution = 2048;                    // 28BYJ-48 has 2048 steps for a full revolution
const int stepsPerQuarterTurn = stepsPerRevolution / 4; // 90-degree rotation

// Components setup
Servo myservo;                      // Servo motor (for rejection mechanism)
LiquidCrystal_I2C lcd(0x27, 16, 2); // LCD with I2C
int redLED = 6;
int greenLED = 7;
int buzzer = 5;
int ledStrip = 4;
int servoPin = 8;

void setup()
{
    // Initialize Serial communication
    Serial.begin(9600);
    Serial.println("Arduino is ready");

    // Initialize components
    myservo.attach(servoPin);
    pinMode(redLED, OUTPUT);
    pinMode(greenLED, OUTPUT);
    pinMode(buzzer, OUTPUT);
    pinMode(ledStrip, OUTPUT);

    // Initialize stepper motor pins
    pinMode(STEPPER_PIN_1, OUTPUT);
    pinMode(STEPPER_PIN_2, OUTPUT);
    pinMode(STEPPER_PIN_3, OUTPUT);
    pinMode(STEPPER_PIN_4, OUTPUT);

    lcd.init();
    lcd.backlight();

    // Print a test message
    lcd.setCursor(0, 0);
    lcd.print("Hello, World!");
    lcd.setCursor(0, 1);
    lcd.print("LCD I2C Test");

    // Default to everything off
    resetAllDevices();
}

void loop()
{
    // Check if there's serial data available
    if (Serial.available() > 0)
    {
        String command = Serial.readString();
        command.trim(); // Trim any whitespace

        // Handle commands
        if (command == "START")
        {
            Serial.println("startProcess...");
            startProcess();
        }
        else if (command == "DEFECT")
        {
            Serial.println("handleDefect...");
            handleDefect();
        }
        else if (command == "NORMAL")
        {
            Serial.println("handleNormal...");
            handleNormal();
        }
        else if (command == "RESET")
        {
            Serial.println("Resetting devices...");
            resetAllDevices();
        }
        else
        {
            Serial.println("Unknown command...");
            lcd.clear();
            lcd.print("Unknown Command");
        }
    }
    else
    {
        // If no command has been received yet, print "Waiting..."
        Serial.println("Waiting...");
    }
}

// Function to rotate stepper motor at 90-degree intervals (total 360 degrees)
void startProcess()
{
    lcd.clear();
    lcd.print("Processing...");

    // Turn on the LED strip
    digitalWrite(ledStrip, HIGH);
    delay(1000);

    // Rotate the stepper motor at 90-degree intervals
    for (int i = 0; i < 4; i++)
    {
        rotateStepper(90); // Rotate 90 degrees
        delay(1000);       // Simulate capturing an image after each 90-degree rotation
        Serial.println("Image Captured");
    }

    // Turn off the LED strip after the rotation is complete
    digitalWrite(ledStrip, LOW);

    // Feedback
    lcd.clear();
    lcd.print("Process Done");
}

// Function to rotate the stepper motor by a specific degree
void rotateStepper(int degrees)
{
    int steps = (degrees / 90) * stepsPerQuarterTurn; // Calculate number of steps for 90 degrees
    for (int i = 0; i < steps; i++)
    {
        OneStep(true);
        delay(10); // Adjust delay based on motor speed requirement
    }
}

// Stepper motor control logic
void OneStep(bool dir)
{
    static int step_number = 0; // Make step_number static to keep its value between function calls
    if (dir)
    {
        switch (step_number)
        {
        case 0:
            digitalWrite(STEPPER_PIN_1, HIGH);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, LOW);
            break;
        case 1:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, HIGH);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, LOW);
            break;
        case 2:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, HIGH);
            digitalWrite(STEPPER_PIN_4, LOW);
            break;
        case 3:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, HIGH);
            break;
        }
    }
    else
    {
        switch (step_number)
        {
        case 0:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, HIGH);
            break;
        case 1:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, HIGH);
            digitalWrite(STEPPER_PIN_4, LOW);
            break;
        case 2:
            digitalWrite(STEPPER_PIN_1, LOW);
            digitalWrite(STEPPER_PIN_2, HIGH);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, LOW);
            break;
        case 3:
            digitalWrite(STEPPER_PIN_1, HIGH);
            digitalWrite(STEPPER_PIN_2, LOW);
            digitalWrite(STEPPER_PIN_3, LOW);
            digitalWrite(STEPPER_PIN_4, LOW);
        }
    }
    step_number++;
    if (step_number > 3)
    {
        step_number = 0;
    }
}

// Handle defective tin (Red LED, Buzzer, Servo rejection mechanism)
void handleDefect()
{
    lcd.clear();
    lcd.print("Defect Detected");

    // Turn on red LED and buzzer
    digitalWrite(redLED, HIGH);
    digitalWrite(buzzer, HIGH);

    delay(2000); // 2-second alert

    // Activate servo for rejection
    myservo.write(180); // Rotate servo to 180 degrees to reject
    delay(1000);        // Wait for rejection
    myservo.write(0);   // Return servo to 0 degrees

    // Turn off red LED and buzzer
    digitalWrite(redLED, LOW);
    digitalWrite(buzzer, LOW);

    lcd.clear();
    lcd.print("Await Command");
}

// Handle normal tin (Green LED)
void handleNormal()
{
    lcd.clear();
    lcd.print("Normal Detected");

    // Turn on green LED
    digitalWrite(greenLED, HIGH);

    delay(2000); // 2-second green LED

    // Turn off green LED
    digitalWrite(greenLED, LOW);

    lcd.clear();
    lcd.print("Await Command");
}

// Reset all devices to normal state
void resetAllDevices()
{
    lcd.clear();
    lcd.print("Resetting...");

    // Turn off LEDs, Buzzer, and reset servo position
    digitalWrite(redLED, LOW);
    digitalWrite(greenLED, LOW);
    digitalWrite(buzzer, LOW);
    myservo.write(0); // Return servo to 0 degrees

    // Clear the LCD display
    lcd.clear();
    lcd.print("All Devices Off");
    delay(2000); // Delay to view the reset message
}