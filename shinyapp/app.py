from shiny import App, render, ui

app_ui = ui.page_fluid(
    ui.h2("Hello Group 9!"),
)

def server(input, output, session):
    ...

app = App(app_ui, server)
