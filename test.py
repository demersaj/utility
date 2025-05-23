from unstructured.partition.pdf import partition_pdf

elements = partition_pdf(
	filename="/Users/huxley-47/Downloads/docs/car/teen_car.maintenance.pdf",
	strategy="hi_res",
	extract_images_in_pdf=True,                            # mandatory to set as ``True``
    extract_image_block_types=["Image", "Table"],          # optional
    extract_image_block_to_payload=True                    # optional
    #extract_image_block_output_dir="/Users/huxley-47/Desktop",  # optional - only works when ``extract_image_block_to_payload=False``
    )
with open("output.txt", "a") as f:
  print("\n\n".join([str(el) for el in elements]), file=f)
f.close()	
