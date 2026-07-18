#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <stdbool.h>
#include <stdint.h>

#include <camera/camera_api.h>


static volatile bool got_frame = false;


typedef struct
{
    const char *filename;
} camera_context_t;



static void processCameraData(
        camera_handle_t handle,
        camera_buffer_t* buffer,
        void* arg)
{
    (void)handle;


    camera_context_t *context = (camera_context_t *)arg;


    if (got_frame)
        return;


    printf("Frame received\n");


    /*
     * Make sure the camera format is what we expect.
     */
    if (buffer->frametype != CAMERA_FRAMETYPE_RGB8888)
    {
        printf(
            "Unsupported frame format: %d\n",
            buffer->frametype
        );

        return;
    }


    uint32_t width =
        buffer->framedesc.rgb8888.width;

    uint32_t height =
        buffer->framedesc.rgb8888.height;

    uint32_t stride =
        buffer->framedesc.rgb8888.stride;


    printf(
        "Image size: %ux%u stride=%u\n",
        width,
        height,
        stride
    );


    FILE *fp = fopen(context->filename, "wb");


    if (!fp)
    {
        printf(
            "Cannot open output file: %s\n",
            context->filename
        );

        return;
    }


    /*
     * RGB8888:
     * 4 bytes per pixel
     *
     * Use stride because rows may contain padding.
     */
    for (uint32_t y = 0; y < height; y++)
    {
        fwrite(
            buffer->framebuf + (y * stride),
            1,
            width * 4,
            fp
        );
    }


    fclose(fp);


    printf(
        "Saved %s\n",
        context->filename
    );


    got_frame = true;
}



int main(int argc, char *argv[])
{
    int err;


    const char *output_file = "/tmp/image.raw";


    /*
     * Allow Python to specify output path:
     *
     * ./capture_image filename.raw
     */
    if (argc > 1)
    {
        output_file = argv[1];
    }



    camera_handle_t handle;


    /*
     * Change this if QNX reports
     * another camera unit.
     */
    camera_unit_t unit = CAMERA_UNIT_0;



    err = camera_open(
            unit,
            CAMERA_MODE_RO,
            &handle);


    if (err != CAMERA_EOK)
    {
        printf(
            "camera_open failed %d\n",
            err
        );

        return 1;
    }



    camera_context_t context;

    context.filename = output_file;



    err = camera_start_viewfinder(
            handle,
            processCameraData,
            &context,
            NULL);



    if (err != CAMERA_EOK)
    {
        printf(
            "camera_start_viewfinder failed %d\n",
            err
        );

        camera_close(handle);

        return 1;
    }



    /*
     * Wait until one frame is captured.
     */
    while (!got_frame)
    {
        usleep(10000);
    }



    camera_stop_viewfinder(handle);


    camera_close(handle);


    return 0;
}`