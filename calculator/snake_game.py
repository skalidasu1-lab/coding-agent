"""
Snake Game - A classic snake game built with pygame.

Controls:
    Arrow Keys or WASD: Move the snake
    P: Pause the game
    R: Restart (on game over screen)
    Q: Quit (on game over screen)
    ESC: Quit the game
"""

import pygame
import random
import sys

# Initialize pygame
pygame.init()

# --- Constants ---
WIDTH = 600
HEIGHT = 400
GRID_SIZE = 20
GRID_WIDTH = WIDTH // GRID_SIZE
GRID_HEIGHT = HEIGHT // GRID_SIZE
FPS = 10

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
DARK_GREEN = (0, 200, 0)
RED = (255, 0, 0)
DARK_RED = (200, 0, 0)
GRAY = (50, 50, 50)
YELLOW = (255, 255, 0)

# Directions
UP = (0, -GRID_SIZE)
DOWN = (0, GRID_SIZE)
LEFT = (-GRID_SIZE, 0)
RIGHT = (GRID_SIZE, 0)


class Snake:
    """Represents the snake in the game."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset the snake to its initial state."""
        start_x = WIDTH // 4
        start_y = HEIGHT // 2
        self.body = [
            [start_x, start_y],
            [start_x - GRID_SIZE, start_y],
            [start_x - 2 * GRID_SIZE, start_y],
        ]
        self.direction = RIGHT
        self.next_direction = RIGHT
        self.grow = False

    def change_direction(self, new_direction):
        """Change the snake's direction if it's not a 180-degree turn."""
        opposites = {
            UP: DOWN,
            DOWN: UP,
            LEFT: RIGHT,
            RIGHT: LEFT,
        }
        if new_direction != opposites.get(self.direction):
            self.next_direction = new_direction

    def move(self):
        """Move the snake one step in its current direction."""
        self.direction = self.next_direction
        head = self.body[0].copy()
        head[0] += self.direction[0]
        head[1] += self.direction[1]

        # Wrap around screen edges (optional - comment out to make walls deadly)
        # head[0] %= WIDTH
        # head[1] %= HEIGHT

        self.body.insert(0, head)

        if not self.grow:
            self.body.pop()
        else:
            self.grow = False

    def grow_snake(self):
        """Mark the snake to grow on the next move."""
        self.grow = True

    def check_self_collision(self):
        """Return True if the snake's head collides with its body."""
        return self.body[0] in self.body[1:]

    def check_wall_collision(self):
        """Return True if the snake's head hits a wall."""
        head = self.body[0]
        return head[0] < 0 or head[0] >= WIDTH or head[1] < 0 or head[1] >= HEIGHT

    def draw(self, surface):
        """Draw the snake on the given surface."""
        for i, segment in enumerate(self.body):
            color = GREEN if i == 0 else DARK_GREEN
            pygame.draw.rect(
                surface, color,
                (segment[0], segment[1], GRID_SIZE - 1, GRID_SIZE - 1)
            )


class Food:
    """Represents the food in the game."""

    def __init__(self):
        self.position = [0, 0]
        self.spawn([])

    def spawn(self, snake_body):
        """Spawn food at a random position not on the snake."""
        while True:
            pos = [
                random.randrange(1, GRID_WIDTH) * GRID_SIZE,
                random.randrange(1, GRID_HEIGHT) * GRID_SIZE,
            ]
            if pos not in snake_body:
                self.position = pos
                break

    def draw(self, surface):
        """Draw the food on the given surface."""
        pygame.draw.rect(
            surface, RED,
            (self.position[0], self.position[1], GRID_SIZE - 1, GRID_SIZE - 1)
        )


class Game:
    """Main game class that manages the game state and loop."""

    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Snake Game")
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont("arial", 24)
        self.font_large = pygame.font.SysFont("arial", 48)
        self.reset_game()

    def reset_game(self):
        """Reset the game to its initial state."""
        self.snake = Snake()
        self.food = Food()
        self.food.spawn(self.snake.body)
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.paused = False
        self.running = True

    def handle_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                    elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        self.running = False
                    return

                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return

                if event.key == pygame.K_p:
                    self.paused = not self.paused
                    return

                if self.paused:
                    return

                # Movement controls
                if event.key in (pygame.K_UP, pygame.K_w):
                    self.snake.change_direction(UP)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    self.snake.change_direction(DOWN)
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.snake.change_direction(LEFT)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.snake.change_direction(RIGHT)

    def update(self):
        """Update the game state."""
        if self.game_over or self.paused:
            return

        self.snake.move()

        # Check wall collision
        if self.snake.check_wall_collision():
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            return

        # Check self collision
        if self.snake.check_self_collision():
            self.game_over = True
            if self.score > self.high_score:
                self.high_score = self.score
            return

        # Check food collision
        if self.snake.body[0] == self.food.position:
            self.snake.grow_snake()
            self.score += 1
            self.food.spawn(self.snake.body)

    def draw_grid(self):
        """Draw the grid lines on the screen."""
        for x in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRAY, (x, 0), (x, HEIGHT))
        for y in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRAY, (0, y), (WIDTH, y))

    def draw_score(self):
        """Draw the current score on the screen."""
        score_text = self.font_small.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_text, (10, 10))
        high_text = self.font_small.render(f"High Score: {self.high_score}", True, WHITE)
        self.screen.blit(high_text, (10, 35))

    def draw_pause(self):
        """Draw the pause overlay."""
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        pause_text = self.font_large.render("PAUSED", True, WHITE)
        text_rect = pause_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(pause_text, text_rect)

    def draw_game_over(self):
        """Draw the game over screen."""
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))

        over_text = self.font_large.render("GAME OVER", True, RED)
        over_rect = over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        self.screen.blit(over_text, over_rect)

        score_text = self.font_small.render(f"Final Score: {self.score}", True, WHITE)
        score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10))
        self.screen.blit(score_text, score_rect)

        high_text = self.font_small.render(f"High Score: {self.high_score}", True, YELLOW)
        high_rect = high_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        self.screen.blit(high_text, high_rect)

        restart_text = self.font_small.render("Press R to Restart", True, WHITE)
        restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.screen.blit(restart_text, restart_rect)

        quit_text = self.font_small.render("Press Q to Quit", True, WHITE)
        quit_rect = quit_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 90))
        self.screen.blit(quit_text, quit_rect)

    def draw(self):
        """Draw all game elements."""
        self.screen.fill(BLACK)
        self.draw_grid()
        self.snake.draw(self.screen)
        self.food.draw(self.screen)
        self.draw_score()

        if self.paused:
            self.draw_pause()
        elif self.game_over:
            self.draw_game_over()

        pygame.display.flip()

    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    """Entry point for the snake game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()