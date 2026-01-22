# Image Browser UI Specifications

## Design System

### Colors
- Background: Dark theme with gradient (20, 20, 24 to 30, 30, 35)
- Cards: Semi-transparent overlay (rgba(255, 255, 255, 0.1))
- Text: White and light gray variations
- Accents: Subtle gradients for interactive elements

### Typography
- Main Font: System font stack, sans-serif
- Card Titles: 16px, semi-bold
- Metadata: 14px, regular
- Navigation: 15px, medium

### Layout
- Grid System: Responsive 4-column layout
- Card Aspect Ratio: 3:4
- Margins: 24px outer, 16px between cards
- Border Radius: 12px for cards, 8px for buttons
- Padding: 16px internal card padding

### Components

#### Navigation Bar
- Height: 64px
- Logo left aligned
- Right-aligned icons for:
  - Home
  - Search
  - Notifications
  - Gallery
  - User Profile

#### Search Bar
- Centered in header area
- Dark overlay background
- Search icon right-aligned
- Rounded corners (24px)
- Placeholder text with medium opacity

#### Image Cards
- Rounded corners
- Title overlay at bottom
- Metadata below title
- Hover effect with subtle scale
- Shadow on hover

#### Sidebar Menu
- Width: 240px
- Icon + Text items
- Selected state indicator
- Category grouping

## Interactions

### Hover States
- Cards: Scale 1.02
- Buttons: Opacity change
- Links: Subtle underline

### Animations
- Card hover: 200ms ease-out
- Menu transitions: 150ms ease
- Search focus: Subtle expand

## Responsive Behavior
- Grid adjusts columns based on viewport
- Sidebar collapses to icon-only on smaller screens
- Cards maintain aspect ratio
- Search bar adapts width

## Accessibility
- High contrast text
- Clear focus states
- Keyboard navigation support
- Alt text for all images 