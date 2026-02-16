class StoryState:
    """Tracks the player's progress through a single story"""
    def __init__(self, story_id, current_scene_id, variables=None, visited_scenes=None):
        self.story_id = story_id
        self.current_scene_id = current_scene_id
        self.variables = variables or {}
        self.visited_scenes = visited_scenes or []

class Scene:
    """
    Represents a scene in the story
    """
    def __init__(self, scene_id, background, choices, conditions=None):
        self.id = scene_id
        self.background = background
        self.choices = choices or []
        self.conditions = conditions or {}

class Choice:
    """
    Represents a choice available in a scene
    """
    def __init__(self, scene_id, text, target_scene_id, conditions=None, effects=None):
        self.id = scene_id
        self.text = text
        self.target_scene_id = target_scene_id
        self.conditions = conditions or {}
        self.effects = effects or {}