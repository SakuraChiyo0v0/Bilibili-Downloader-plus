class FFmpegCommand:
    def __init__(self):
        self.inputs = []
        self.outputs = []
        self.params = []

    def add_input(self, input_path: str):
        self.inputs.append(input_path)

        return self

    def add_output(self, output_path: str):
        self.outputs.append(output_path)

        return self

    def add_param(self, *args: str):
        self.params.extend(args)

        return self

    def build(self):
        command = ["ffmpeg", "-y"]

        for input_path in self.inputs:
            command.extend(["-i", input_path])

        command.extend(self.params)

        for output_path in self.outputs:
            command.append(output_path)

        return command
    
    @classmethod
    def merge_video_audio(cls, video_path: str, audio_path: str, output_path: str, cover_path: str = None, metadata: dict = None):
        if cover_path:
            cmd = (
                cls()
                .add_input(video_path)
                .add_input(audio_path)
                .add_input(cover_path)
                .add_param("-map", "0:v:0")
                .add_param("-map", "1:a:0")
                .add_param("-map", "2:v:0")
                .add_param("-c:v", "copy")
                .add_param("-c:a", "copy")
                .add_param("-c:v:1", "mjpeg")
                .add_param("-disposition:v:1", "attached_pic")
                .add_param("-pix_fmt:v:1", "yuvj420p")
            )
        else:
            cmd = (
                cls()
                .add_input(video_path)
                .add_input(audio_path)
                .add_param("-c:v", "copy")
                .add_param("-c:a", "copy")
            )
        
        if metadata:
            for key, value in metadata.items():
                cmd.add_param("-metadata", f"{key}={value}")
        
        return cmd.add_output(output_path)
    
    @classmethod
    def merge_video_parts(cls, lists_path: str, output_path: str, cover_path: str = None, metadata: dict = None):
        if cover_path:
            cmd = (
                cls()
                .add_input(cover_path)
                .add_param("-f", "concat")
                .add_param("-safe", "0")
                .add_param("-i", lists_path)
                .add_param("-c:v", "copy")
                .add_param("-c:a", "copy")
                .add_param("-map", "1:v:0")
                .add_param("-map", "0:v:0")
                .add_param("-c:v:1", "mjpeg")
                .add_param("-disposition:v:1", "attached_pic")
                .add_param("-pix_fmt:v:1", "yuvj420p")
            )
        else:
            cmd = (
                cls()
                .add_param("-f", "concat")
                .add_param("-safe", "0")
                .add_param("-i", lists_path)
                .add_param("-c:v", "copy")
                .add_param("-c:a", "copy")
            )
        
        if metadata:
            for key, value in metadata.items():
                cmd.add_param("-metadata", f"{key}={value}")
        
        return cmd.add_output(output_path)

    @classmethod
    def convert_m4a_to_mp3(cls, input_path: str, output_path: str, cover_path: str = None, metadata: dict = None):
        if cover_path:
            cmd = (
                cls()
                .add_input(input_path)
                .add_input(cover_path)
                .add_param("-map", "0:a:0")
                .add_param("-map", "1:v:0")
                .add_param("-c:a", "libmp3lame")
                .add_param("-q:a", "2")
                .add_param("-c:v:0", "mjpeg")
                .add_param("-disposition:v:0", "attached_pic")
                .add_param("-id3v2_version", "3")
            )
        else:
            cmd = (
                cls()
                .add_input(input_path)
                .add_param("-c:a", "libmp3lame")
                .add_param("-q:a", "2")
            )
        
        if metadata:
            for key, value in metadata.items():
                cmd.add_param("-metadata", f"{key}={value}")
        
        return cmd.add_output(output_path)
    
    @classmethod
    def fix_mp4_box(cls, input_path: str, output_path: str):
        return (
            cls()
            .add_input(input_path)
            .add_param("-c", "copy")
            .add_param("-movflags", "+faststart")
            .add_output(output_path)
        )

    @classmethod
    def attach_cover_to_m4a(cls, input_path: str, output_path: str, cover_path: str, metadata: dict = None):
        cmd = (
            cls()
            .add_input(input_path)
            .add_input(cover_path)
            .add_param("-map", "0:a:0")
            .add_param("-map", "1:v:0")
            .add_param("-c:a", "copy")
            .add_param("-c:v:0", "mjpeg")
            .add_param("-disposition:v:0", "attached_pic")
            .add_param("-pix_fmt:v:0", "yuvj420p")
        )
        
        if metadata:
            for key, value in metadata.items():
                cmd.add_param("-metadata", f"{key}={value}")
        
        return cmd.add_output(output_path)