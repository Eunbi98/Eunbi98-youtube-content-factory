from config.settings import ensure_directories
from app.services.pipeline_service import PipelineService


def main():
    ensure_directories()

    pipeline = PipelineService()
    pipeline.run()


if __name__ == "__main__":
    main()