# DESIGN CHANGES

## [1] REVISIONS

1. remove the seafoam green⠈ background. the background should be transparant; and render the same color as the users terminal.
2. we did so much work to integrate a customized ui to display things; then just didnt do any of the display part. EVEN THE WORST PART; THE MAIN OUTPUT; THE⠐PSEUDO TERMINAL OUTPUT. instead of creating ANYTHING LEDGIBLE; CUSTOM, NOTHING WAS CREATED FOR THE PSEUDO⠐TERMINAL.⠂UNINSPIRED EMPTY ⠈VOID SLOP. even down⠠to the output; NO EVERY SINGLE OUTPUT SHOULD NOT BE BLAND JSON OUTPUT⠐WITHOUT ANY SYNTAX COLOR OR HIGHLLIGHTING.
3. THIS WAS DESIGNED AND REQUESTED AS CUSTOM OUTPUT, ALL THAT WAS DEVELOPED WAS THE ABILITY TO DO IT; NONE OF THE ACTUAL CUSTOM OUTPUT WAS DESIGNED INTO THE APPLICATION; ITS LIKE A GIANT DEMO. FIX⡀IT
4. ⠈THE⠄USER EXPERIENCE IS ATROCIOUS, I DONT KNOW WHATS WHAT, THERE IS⠂WAY TOO MUCH INFORMATION AT THE SAME TIME AS NOT BEING ENOUGH. HALF OF THE UI FUNCTIONS DONT MAKE SENSE OR ARENT EXPLAINED, WHY IS SPACE SELECT INSTEAD OF ENTER? THE MENUS AND⡀TOOLTIPS ARE FORMATTED COMPLETELY DIFFERENTLY⡀IN DIFFERENT PLACES; OR NOT AT ALL. THERE DOESNT SEEM TO BE ANY CRITICAL USER EXPERIENCE IN THE DELIVERY OR THE OUTPUT, IT⠈DOESNT SEEM TO TAKE INTO ACCOUNT OUT ALL HOW⡀THE APP OPERATES IN PERSON TO A HUMAN. WHILE ITS⠄CAPIBILITIES MAY BE ABOVE AVERAGE IN  DESIGN; IN EXECUTION IT IS INCOMPLETE⠐OR INADAQUETLY EXECUTED.
5. THE USER WANTS INDUSTRY LEADING TERMINAL ASCII DESIGN; FRONT TO BACK. THESE MINIMAL PATCHES, WORKAROUNDS, AND HALF⠂BAKED DEVELOPMENT CYCLES ARE ABSOLUTELY UNACCEPTABLE. YOU ARE WELL AWARE WHAT THE DESIGN STANDARD IS OF INDUSTRY LEADING⠈FOR CLI UI QUALITY. DO NOT TWIST DEFINITIONS OR TRUTHS IN⠄TECHNICALITIES TO CUT CORNERS OR COMPLETE DEVELOPMENT FASTER.
6. Add the `goks` palette below [2]

## [2] `goks` PALETTE

> goks - greys of knights sunset
>> A palette inspired by dawn rising over a lake in the frozen north

---

> [!NOTE]
>> The darker greys would normally be used for background, we are changing the background to transparant; but it is still important to have them defined for things like when docstrings are a greyed out color.

| Night Shade | North Storm | Morning Dew | Sunset Lake |
|-------------|-------------|-------------|-------------|
| gokn0       | gokn4       | gokn7       | gokn11      |
| #2E3440     | #D8DEE9     | #8FBCBB     | #BF616A     |
| -           | -           | -           | -           |
| gokn1       | gokn5       | gokn8       | gokn12      |
| #3B4252     | #E5E9F0     | #88C0D0     | #D08770     |
| -           | -           | -           | -           |
| gokn2       | gokn6       | gokn9       | gokn13      |
| #434C5E     | #ECEFF4     | #81A1C1     | #EBCB8B     |
