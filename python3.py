import pygame
import random
import sys
from pyfirmata import Arduino, util
import time

# Initialize Pygame
pygame.init()

# Screen Setup
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Flappy Bird with Arduino")

# Game Settings
GRAVITY = 0.25
FLAP_STRENGTH = -7
PIPE_SPEED = 3
PIPE_GAP = 150
PIPE_FREQUENCY = 1500  # milliseconds

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
SKY_BLUE = (135, 206, 235)

# Font
font = pygame.font.SysFont('Arial', 30)
clock = pygame.time.Clock()

# Arduino Setup
try:
    board = Arduino('COM3')  # Change to your port (e.g., '/dev/ttyACM0' for Linux)
    button_pin = 2  # Push button on Digital Pin 2
    board.digital[button_pin].mode = pyfirmata.INPUT
    iterator = util.Iterator(board)
    iterator.start()
    print("Arduino connected successfully!")
except Exception as e:
    print(f"Arduino connection failed: {e}")
    board = None

class Bird:
    def __init__(self):
        self.x = 100
        self.y = SCREEN_HEIGHT // 2
        self.velocity = 0
        self.width = 40
        self.height = 30
        self.color = (255, 255, 0)  # Yellow
    
    def flap(self):
        self.velocity = FLAP_STRENGTH
    
    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity
        
        # Prevent bird from flying out of screen
        if self.y < 0:
            self.y = 0
            self.velocity = 0
    
    def draw(self):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        pygame.draw.circle(screen, BLACK, (self.x + 30, self.y + 10), 5)  # Eye
        pygame.draw.polygon(screen, (255, 165, 0), [  # Beak
            (self.x + 40, self.y + 15),
            (self.x + 50, self.y + 15),
            (self.x + 40, self.y + 20)
        ])
    
    def get_mask(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Pipe:
    def __init__(self):
        self.x = SCREEN_WIDTH
        self.height = random.randint(100, SCREEN_HEIGHT - 100 - PIPE_GAP)
        self.top_pipe = pygame.Rect(self.x, 0, 60, self.height)
        self.bottom_pipe = pygame.Rect(self.x, self.height + PIPE_GAP, 60, SCREEN_HEIGHT - self.height - PIPE_GAP)
        self.passed = False
    
    def update(self):
        self.x -= PIPE_SPEED
        self.top_pipe.x = self.x
        self.bottom_pipe.x = self.x
    
    def draw(self):
        pygame.draw.rect(screen, GREEN, self.top_pipe)
        pygame.draw.rect(screen, GREEN, self.bottom_pipe)
    
    def collide(self, bird):
        bird_mask = bird.get_mask()
        return bird_mask.colliderect(self.top_pipe) or bird_mask.colliderect(self.bottom_pipe)

def draw_score(score):
    score_text = font.render(f"Score: {score}", True, BLACK)
    screen.blit(score_text, (10, 10))

def game_over_screen(score):
    screen.fill(SKY_BLUE)
    game_over_text = font.render("Game Over", True, BLACK)
    score_text = font.render(f"Score: {score}", True, BLACK)
    restart_text = font.render("Press Button, SPACE, or Click", True, BLACK)
    
    screen.blit(game_over_text, (SCREEN_WIDTH//2 - game_over_text.get_width()//2, SCREEN_HEIGHT//2 - 60))
    screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2))
    screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 60))
    
    pygame.display.update()
    
    waiting = True
    while waiting:
        # Check Arduino button
        if board and board.digital[button_pin].read():
            waiting = False
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                waiting = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                waiting = False
        
        clock.tick(60)

def check_button_press():
    if board:
        try:
            return board.digital[button_pin].read()  # Returns True if button pressed
        except:
            return False
    return False

def main():
    bird = Bird()
    pipes = []
    score = 0
    last_pipe = pygame.time.get_ticks()
    game_active = True
    
    running = True
    while running:
        # Check Arduino button
        button_pressed = check_button_press()
        
        # Event Handling (Keyboard, Mouse, Arduino)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if game_active:
                    bird.flap()
                else:
                    # Reset game
                    bird = Bird()
                    pipes = []
                    score = 0
                    last_pipe = pygame.time.get_ticks()
                    game_active = True
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_active:
                    bird.flap()
                else:
                    # Reset game
                    bird = Bird()
                    pipes = []
                    score = 0
                    last_pipe = pygame.time.get_ticks()
                    game_active = True
        
        # Arduino Button Control
        if button_pressed:
            if game_active:
                bird.flap()
            else:
                # Reset game
                bird = Bird()
                pipes = []
                score = 0
                last_pipe = pygame.time.get_ticks()
                game_active = True
        
        if game_active:
            bird.update()
            
            # Generate Pipes
            current_time = pygame.time.get_ticks()
            if current_time - last_pipe > PIPE_FREQUENCY:
                pipes.append(Pipe())
                last_pipe = current_time
            
            # Update Pipes
            for pipe in pipes[:]:
                pipe.update()
                
                # Collision Check
                if pipe.collide(bird):
                    game_active = False
                
                # Score Update
                if not pipe.passed and pipe.x < bird.x:
                    pipe.passed = True
                    score += 1
                
                # Remove Off-Screen Pipes
                if pipe.x < -60:
                    pipes.remove(pipe)
            
            # Check if bird hits ground or ceiling
            if bird.y + bird.height >= SCREEN_HEIGHT or bird.y < 0:
                game_active = False
        
        # Draw Everything
        screen.fill(SKY_BLUE)
        
        if game_active:
            for pipe in pipes:
                pipe.draw()
            bird.draw()
            draw_score(score)
        else:
            game_over_screen(score)
        
        pygame.display.update()
        clock.tick(60)
    
    # Cleanup
    if board:
        board.exit()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()