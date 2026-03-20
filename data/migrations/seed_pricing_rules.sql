-- Pricing Rules seed data
-- Generated: 2026-02-02T14:10:57.767605+00:00
-- Source: data/materials/pricing_model.csv

BEGIN;

-- Materials
INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '2025a3e3-a776-4490-97ac-25b520c04e27', 'Ring mechanism / closure mechanism', 'MECHANISM', 'Extracted from pricing model: MECHANISM (number)', 'hardware', 'unit', 0.5, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  'eaf7df3e-6c5c-4b1b-9e1b-a94a621dd08a', 'Dutch grey board sheet', 'COST-PER-SHEET-OF-DUTCH-GREY-B', 'Extracted from pricing model: COST PER SHEET OF DUTCH GREY BOARD (number)', 'board', 'sheet', 1.3, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '4ddacc32-09a6-4288-9fa6-74b07b7756c4', 'Liner paper sheet', 'COST-PER-SHEET-OF-LINER-PAPER', 'Extracted from pricing model: COST PER SHEET OF LINER PAPER (number)', 'paper', 'sheet', 0.18, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '85439776-700f-4395-9d6c-d70c53350673', 'Printed and laminated outer sheets', 'PRINTED-AND-LAMINATED-OUTER-SH', 'Extracted from pricing model: PRINTED AND LAMINATED OUTER SHEETS (number)', 'paper', 'sheet', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  'c3a9daa4-791e-4104-ad9b-33f82540a784', 'Printed and laminated inner sheets', 'PRINTED-AND-LAMINATED-INNER-SH', 'Extracted from pricing model: PRINTED AND LAMINATED INNER SHEETS (number)', 'paper', 'sheet', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '604fb188-6d2a-4acb-a337-7ce60b5e20e8', 'Ring mechanism / closure mechanism', 'MECHANISM-1', 'Extracted from pricing model: MECHANISM (number).1', 'hardware', 'unit', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  'b389816c-a457-42c1-822f-34fbd793aff7', 'Digital printing / foil / screenprint finishing', 'DIGITAL-FOIL-SCREENPRINTING', 'Extracted from pricing model: DIGITAL/FOIL/SCREENPRINTING (number)', 'finishing', 'unit', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '87d6c658-5d61-424c-9c1e-bba130d7f811', 'PVA adhesive for binding', 'GLUE-COST-PER-BINDER', 'Extracted from pricing model: GLUE COST PER BINDER (number)', 'adhesive', 'sqm', 0.1, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  'f33c5a99-1c40-4577-9f7f-fdc3835801b8', 'Magnetic closure (single magnet)', 'SINGLE-MAGNET-COST-GBP0-10-PEN', 'Extracted from pricing model: SINGLE MAGNET COST £0.10 PENCE EACH (number)', 'hardware', 'unit', 0.1, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '38e6fea1-37c5-41f4-be48-5afc9abaf025', 'Binding rivets', 'NUMBER-OF-RIVETS-PER-BINDER', 'Extracted from pricing model: NUMBER OF RIVETS PER BINDER (number)', 'hardware', 'unit', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '31eb4427-57b7-441c-a4e5-8ce6b00d4418', 'Custom cutting forme/die', 'CUTTING-FORME-COST-IF-REQUIRED', 'Extracted from pricing model: CUTTING FORME COST IF REQUIRED (number)', 'consumable', 'unit', 0.0, true, NOW(), NOW()
);

INSERT INTO materials (id, name, sku, description, category, unit, current_price, is_active, created_at, updated_at) VALUES (
  '871bb85a-2c8a-453d-9464-8f11b541e8cb', 'Pallet packing materials (wrap, strapping)', 'PACKING-MATERIALS-PER-PALLETE', 'Extracted from pricing model: PACKING MATERIALS PER PALLETE (number)', 'consumable', 'unit', 20.0, true, NOW(), NOW()
);


-- Pricing Rules
INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '4331b826-3a21-49c8-a464-9251a7099835', 'one_item', 'ONE ITEM (number)', 'Legacy variable: ONE ITEM (number)', 'calculated', 'one_item', ARRAY['quantity_including_overs'], 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '468c9318-99a1-4708-bdf7-da0baebe7ee2', 'quantity_required_by_customer', 'QUANTITY REQUIRED BY CUSTOMER (number)', 'Legacy variable: QUANTITY REQUIRED BY CUSTOMER (number)', 'customer_variable', 'quantity_required_by_customer', ARRAY['mechanism'], 7000.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '2606d9eb-652f-4e81-a034-0cdda7008b49', 'quantity_including_overs', 'QUANTITY INCLUDING OVERS (number)', 'Legacy variable: QUANTITY INCLUDING OVERS (number)', 'calculated', 'quantity_required_by_customer*1.05+50', ARRAY['mechanism', 'quantity_required_by_customer'], 7400.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '08249609-1902-4c58-8df9-37b97bd33660', 'mechanism', 'MECHANISM (number)', 'Legacy variable: MECHANISM (number)', 'overhead', 'mechanism', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '97581acc-7588-4529-9673-066ce2e9ac0f', 'unit_weight_for_carriage', 'UNIT WEIGHT FOR CARRIAGE (kg)', 'Legacy variable: UNIT WEIGHT FOR CARRIAGE (kg)', 'factory_constant', 'unit_weight_for_carriage', NULL, 0.2, 'kg', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'ba095112-5673-4383-b848-cdb9d965706c', 'thickness_of_dutch_grey_board', 'THICKNESS OF DUTCH GREY BOARD (mm)', 'Legacy variable: THICKNESS OF DUTCH GREY BOARD (mm)', 'factory_constant', 'thickness_of_dutch_grey_board', NULL, 2.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '6b8525e8-95e9-46f5-a6ce-f2b230871f86', 'flat_size_length', 'FLAT SIZE Length (mm)', 'Legacy variable: FLAT SIZE Length (mm)', 'customer_variable', 'flat_size_length', NULL, 400.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'ef9af563-9817-4c6a-a5e6-b68db6aaf2cc', 'flat_size_width', 'FLAT SIZE Width (mm)', 'Legacy variable: FLAT SIZE Width (mm)', 'customer_variable', 'flat_size_width', NULL, 400.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '51d730c1-48e8-4dc3-bc2c-2faa1c5ad90b', 'flat_size_area', 'FLAT SIZE Area (m^2)', 'Legacy variable: FLAT SIZE Area (m^2)', 'calculated', 'flat_size_length*flat_size_width/1000000', ARRAY['flat_size_length', 'flat_size_width'], 0.16, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '9252dc2c-fdf8-41f7-affc-d5abb6449aac', 'outer_wrap_size_length', 'OUTER WRAP SIZE Length (mm)', 'Legacy variable: OUTER WRAP SIZE Length (mm)', 'customer_variable', 'flat_size_length+40', ARRAY['flat_size_length'], 440.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a65e7a62-5ae5-4743-8515-e546c2b7c9af', 'outer_wrap_size_width', 'OUTER WRAP SIZE Width (mm)', 'Legacy variable: OUTER WRAP SIZE Width (mm)', 'customer_variable', 'flat_size_width+40', ARRAY['flat_size_width'], 440.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '2df722bc-91c8-48c9-983a-edcaebf5dfef', 'outer_wrap_size_area', 'OUTER WRAP SIZE Area (m^2)', 'Legacy variable: OUTER WRAP SIZE Area (m^2)', 'calculated', 'outer_wrap_size_length*outer_wrap_size_width/1000000', ARRAY['outer_wrap_size_length', 'outer_wrap_size_width'], 0.1936, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '601542b6-6d4a-4c4f-9d99-d1f52c5d4012', 'liner_size_length', 'LINER SIZE Length (mm)', 'Legacy variable: LINER SIZE Length (mm)', 'customer_variable', 'flat_size_length-5', ARRAY['flat_size_length'], 395.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'd5782b9f-f32e-4368-a79e-cac0fd4ec849', 'liner_size_width', 'LINER SIZE Width (mm)', 'Legacy variable: LINER SIZE Width (mm)', 'customer_variable', 'flat_size_width-5', ARRAY['flat_size_width'], 395.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '5751dbb6-db45-4252-a02d-673cb770fe23', 'liner_size_area', 'LINER SIZE Area (m^2)', 'Legacy variable: LINER SIZE Area (m^2)', 'calculated', 'liner_size_length*liner_size_width/1000000', ARRAY['liner_size_length', 'liner_size_width'], 0.156025, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '1c116a8b-908e-4aed-a22a-5548800bd145', 'total_area_for_glue', 'TOTAL AREA FOR GLUE (m^2)', 'Legacy variable: TOTAL AREA FOR GLUE (m^2)', 'calculated', 'outer_wrap_size_area+liner_size_area', ARRAY['liner_size_area', 'outer_wrap_size_area'], 0.3496249999999999, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'ccf0d4c9-e7ba-4106-bb34-a131e51b0efa', 'area_of_dutch_grey_board', 'Area of Dutch Grey Board (m^2)', 'Legacy variable: Area of Dutch Grey Board (m^2)', 'customer_variable', 'area_of_dutch_grey_board', NULL, 1.0, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=0, customer_var=1', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '6e215e90-7fde-490a-b6a3-f3b103101be5', 'yield_per_sheet_of_dutch_grey_board', 'YIELD PER SHEET OF DUTCH GREY BOARD (number)', 'Legacy variable: YIELD PER SHEET OF DUTCH GREY BOARD (number)', 'calculated', 'area_of_dutch_grey_board/flat_size_area', ARRAY['area_of_dutch_grey_board', 'flat_size_area'], 6.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '6ecfa315-f82e-45cc-9671-9a79d14ffbc4', 'drill_max_thickness', 'DRILL MAX THICKNESS (mm)', 'Legacy variable: DRILL MAX THICKNESS (mm)', 'factory_constant', 'drill_max_thickness', NULL, 10.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '8ec62f53-6d77-409e-9e23-c1884159864e', 'drill_up_and_down_cycles_per_hour', 'DRILL UP AND DOWN CYCLES PER HOUR (number)', 'Legacy variable: DRILL UP AND DOWN CYCLES PER HOUR (number)', 'factory_constant', 'drill_up_and_down_cycles_per_hour', NULL, 180.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '100d6680-dcc0-49f8-9530-c59641191ac9', 'drill_up_and_down_totoal_cycles', 'DRILL UP AND DOWN TOTOAL CYCLES (number)', 'Legacy variable: DRILL UP AND DOWN TOTOAL CYCLES (number)', 'calculated', 'total_drilling_thickness/drill_max_thickness', ARRAY['drill_max_thickness', 'total_drilling_thickness'], 2960.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '8b7e1093-4bff-468d-9305-2356558d0edc', 'drill_board', 'DRILL BOARD (number)', 'Legacy variable: DRILL BOARD (number)', 'factory_constant', 'drill_board', NULL, 2.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'fab0f45c-37f9-49c8-ac9b-202825ee8798', 'total_drilling_thickness', 'TOTAL DRILLING THICKNESS (mm)', 'Legacy variable: TOTAL DRILLING THICKNESS (mm)', 'calculated', 'quantity_including_overs*thickness_of_dutch_grey_board*drill_board', ARRAY['drill_board', 'quantity_including_overs', 'thickness_of_dutch_grey_board'], 29600.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a31d5249-3e54-490c-a711-04f480f0e5ef', 'grey_board_sheets', 'GREY BOARD SHEETS (number)', 'Legacy variable: GREY BOARD SHEETS (number)', 'material_cost', 'ceil(quantity_including_overs/yield_per_sheet_of_dutch_grey_board)', ARRAY['quantity_including_overs', 'yield_per_sheet_of_dutch_grey_board'], 1234.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'f11f9987-1476-43a5-a26d-4359417f25ff', 'thickness_of_liner_paper', 'THICKNESS OF LINER PAPER (mm)', 'Legacy variable: THICKNESS OF LINER PAPER (mm)', 'factory_constant', 'thickness_of_liner_paper', NULL, 0.15, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '3a0952fc-8ea2-486b-96fc-02ff24d46e67', 'liner_total_pile_depth', 'Liner Total Pile depth (mm)', 'Legacy variable: Liner Total Pile depth (mm)', 'calculated', 'quantity_including_overs*thickness_of_liner_paper', ARRAY['quantity_including_overs', 'thickness_of_liner_paper'], 1110.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '3b4ad873-65a4-4834-990d-aa0e8bc1f46b', 'dutch_grey_total_pile_depth', 'Dutch Grey Total Pile depth (mm)', 'Legacy variable: Dutch Grey Total Pile depth (mm)', 'calculated', 'quantity_including_overs/yield_per_sheet_of_dutch_grey_board*thickness_of_dutch_grey_board', ARRAY['quantity_including_overs', 'thickness_of_dutch_grey_board', 'yield_per_sheet_of_dutch_grey_board'], 2466.6666666666665, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'd5afd214-b2bc-4767-9bb7-d1ef08a55c56', 'yield_per_sheet_from_liner_paper', 'YIELD PER SHEET FROM LINER PAPER (number)', 'Legacy variable: YIELD PER SHEET FROM LINER PAPER (number)', 'calculated', 'yield_per_sheet_from_liner_paper', NULL, 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '385634e1-bf59-48d8-b5ff-47ea35fdbc18', 'guillotine_pile_depth_grey_board', 'GUILLOTINE PILE DEPTH GREY BOARD (mm)', 'Legacy variable: GUILLOTINE PILE DEPTH GREY BOARD (mm)', 'factory_constant', 'guillotine_pile_depth_grey_board', NULL, 40.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'da6d1a88-0ccf-40c5-b47e-d2be456b1834', 'guillotine_pile_depth_inner_liner_and_outer_supplied_sheets', 'GUILLOTINE PILE DEPTH INNER LINER & OUTER SUPPLIED SHEETS (mm)', 'Legacy variable: GUILLOTINE PILE DEPTH INNER LINER & OUTER SUPPLIED SHEETS (mm)', 'factory_constant', 'guillotine_pile_depth_inner_liner_and_outer_supplied_sheets', NULL, 40.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '4da86540-dcdc-4ec6-980a-81fad549674b', 'pallet_length', 'Pallet Length (mm)', 'Legacy variable: Pallet Length (mm)', 'factory_constant', 'pallet_length', NULL, 1000.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '4c9fa789-59cc-4a98-bbb7-262af1653514', 'pallet_width', 'Pallet Width (mm)', 'Legacy variable: Pallet Width (mm)', 'factory_constant', 'pallet_width', NULL, 1200.0, 'mm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '15a7f302-a587-4aa2-90ef-6502f7ddb522', 'pallet_area', 'Pallet Area (m^2)', 'Legacy variable: Pallet Area (m^2)', 'factory_constant', 'pallet_length*pallet_width/1000000', ARRAY['pallet_length', 'pallet_width'], 1.2, 'sqm', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a6144a7f-3a8b-46ef-9ec2-e8ecc32a6925', 'folders_per_pallet_area', 'FOLDERS PER PALLET AREA (number)', 'Legacy variable: FOLDERS PER PALLET AREA (number)', 'calculated', 'yield_per_sheet_of_dutch_grey_board', ARRAY['yield_per_sheet_of_dutch_grey_board'], 6.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '25ecdf2c-9972-42b1-8b6b-71e261f0e56c', 'folders_per_pallet_height', 'FOLDERS PER PALLET HEIGHT (number)', 'Legacy variable: FOLDERS PER PALLET HEIGHT (number)', 'calculated', 'folders_per_pallet_height', NULL, 500.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '2908018c-ace7-42f5-b0e8-984b198cc7e2', 'folders_per_pallet_volume', 'FOLDERS PER PALLET VOLUME (number)', 'Legacy variable: FOLDERS PER PALLET VOLUME (number)', 'calculated', 'folders_per_pallet_area*folders_per_pallet_height', ARRAY['folders_per_pallet_area', 'folders_per_pallet_height'], 3000.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'f481c972-026c-420b-aa79-840067bec283', 'number_of_pallets', 'NUMBER OF PALLETS (number)', 'Legacy variable: NUMBER OF PALLETS (number)', 'material_cost', 'round(quantity_required_by_customer/folders_per_pallet_volume)', ARRAY['folders_per_pallet_volume', 'quantity_required_by_customer'], 2.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'ba57e3d1-250b-4aec-a955-435efa70c442', 'guillotine_cut_time_dutch_board', 'GUILLOTINE CUT TIME DUTCH BOARD (hours)', 'Legacy variable: GUILLOTINE CUT TIME DUTCH BOARD (hours)', 'factory_constant', '1/60*3', NULL, 0.05, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '11596aad-455c-42bc-96a7-51a63917479c', 'guillotine_cut_time_liner', 'GUILLOTINE CUT TIME LINER (hours)', 'Legacy variable: GUILLOTINE CUT TIME LINER (hours)', 'factory_constant', '1/60*3', NULL, 0.05, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '45ed5bb3-93af-496b-bb1e-a56133e856ea', 'creasing_speed_4_page', 'CREASING SPEED 4 PAGE (per hour)', 'Legacy variable: CREASING SPEED 4 PAGE (per hour)', 'factory_constant', 'creasing_speed_4_page', NULL, 400.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '48f823cc-8dee-4168-a278-8b1ddafaabac', 'creasing_speed_6_page', 'CREASING SPEED 6 PAGE (per hour)', 'Legacy variable: CREASING SPEED 6 PAGE (per hour)', 'factory_constant', 'creasing_speed_6_page', NULL, 300.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'f5f4d89d-085d-4ea9-85de-8df95f20749b', 'creasing_speed_8_page', 'CREASING SPEED 8 PAGE (number per hours)', 'Legacy variable: CREASING SPEED 8 PAGE (number per hours)', 'factory_constant', 'creasing_speed_8_page', NULL, 240.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'd9a13ff4-6797-461d-869c-5d131aed331a', 'admin', 'ADMIN (number)', 'Legacy variable: ADMIN (number)', 'overhead', 'admin', NULL, 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '7ce5c03c-c24e-4386-a2f9-3314988f09a0', 'mac_time', 'MAC TIME (hours)', 'Legacy variable: MAC TIME (hours)', 'labor_time', 'mac_time', NULL, 0.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '37e6dbfb-1c3c-4213-a797-2818532872e9', 'programme_guillotine', 'PROGRAMME GUILLOTINE (job)', 'Legacy variable: PROGRAMME GUILLOTINE (job)', 'overhead', 'programme_guillotine', NULL, 1.0, 'per_job', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'c4cee2d9-2118-4d46-97e8-c601e2cc1833', 'guillotine_dutch_grey_board_40mm', 'GUILLOTINE DUTCH GREY BOARD 40mm (hours)', 'Legacy variable: GUILLOTINE DUTCH GREY BOARD 40mm (hours)', 'labor_time', '1/60*5', ARRAY['guillotine_cut_time_dutch_board', 'guillotine_pile_depth_grey_board', 'quantity_including_overs', 'thickness_of_dutch_grey_board', 'yield_per_sheet_of_dutch_grey_board'], 0.0833333333333333, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '792f5a0b-ae88-4e29-b290-1c838d6db38a', 'trim_4_edges_of_outer_sheet_40mm', 'TRIM 4 EDGES OF OUTER SHEET 40mm (hours)', 'Legacy variable: TRIM 4 EDGES OF OUTER SHEET 40mm (hours)', 'labor_time', '1/60*2', ARRAY['guillotine_pile_depth_inner_liner_and_outer_supplied_sheets', 'liner_total_pile_depth'], 0.0333333333333333, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '8f538b6d-5131-4012-b25a-f956b6e678f8', 'mitre_corners_of_outer_sheet_40mm', 'MITRE CORNERS OF OUTER SHEET 40mm (hours)', 'Legacy variable: MITRE CORNERS OF OUTER SHEET 40mm (hours)', 'labor_time', 'mitre_corners_of_outer_sheet_40mm', ARRAY['guillotine_pile_depth_inner_liner_and_outer_supplied_sheets', 'liner_total_pile_depth'], 0.03, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '44c0c121-7c68-436f-b7ba-50e9dc560e5b', 'guillotine_liner_paper_40mm', 'GUILLOTINE LINER PAPER 40mm (hours)', 'Legacy variable: GUILLOTINE LINER PAPER 40mm (hours)', 'labor_time', '1/60*2', ARRAY['guillotine_pile_depth_inner_liner_and_outer_supplied_sheets', 'liner_total_pile_depth'], 0.0333333333333333, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '9feb5c70-6d0f-431c-b607-f7a50b6cb774', 'set_up_drilling_machine_to_drill_board_for_magnets', 'SET UP DRILLING MACHINE TO DRILL BOARD FOR MAGNETS (hours)', 'Legacy variable: SET UP DRILLING MACHINE TO DRILL BOARD FOR MAGNETS (hours)', 'labor_time', 'set_up_drilling_machine_to_drill_board_for_magnets', NULL, 1.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '52e4a25b-4e32-4e5e-9c77-6b807f873394', 'sheet_stock_from_roll', 'SHEET STOCK FROM ROLL (hours)', 'Legacy variable: SHEET STOCK FROM ROLL (hours)', 'labor_time', 'sheet_stock_from_roll', NULL, 0.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '62164e25-0384-46f1-899e-365763894625', 'precision_trim_panels_from_roll', 'PRECISION TRIM PANELS FROM ROLL (hours)', 'Legacy variable: PRECISION TRIM PANELS FROM ROLL (hours)', 'labor_time', 'precision_trim_panels_from_roll', NULL, 0.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '12e279fe-feca-44a5-9caf-72d2ab6e3039', 'set_up_pob_machine', 'SET UP POB MACHINE (hours)', 'Legacy variable: SET UP POB MACHINE (hours)', 'labor_time', 'set_up_pob_machine', NULL, 3.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '6727bd8e-1de2-4fa7-b816-1c942700ae9c', 'wrap_outer_sheets_to_grey_board', 'WRAP OUTER SHEETS TO GREY BOARD (per hour)', 'Legacy variable: WRAP OUTER SHEETS TO GREY BOARD (per hour)', 'labor_time', 'wrap_outer_sheets_to_grey_board', ARRAY['quantity_including_overs'], 1000.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '841b4b66-1a57-4af7-a95e-f22e0aba8ebd', 'clean_up_pob_machine', 'CLEAN UP POB MACHINE (hours)', 'Legacy variable: CLEAN UP POB MACHINE (hours)', 'labor_time', 'clean_up_pob_machine', NULL, 0.5, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'c71d5e89-9c0e-468d-8337-5874090ee0ec', 'set_up_pob_machine_1', 'SET UP POB MACHINE (hours).1', 'Legacy variable: SET UP POB MACHINE (hours).1', 'labor_time', 'set_up_pob_machine_1', NULL, 3.0, NULL, 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a7e45c7f-4752-4cef-a1d5-fca2d48595eb', 'glue_liner_papers', 'GLUE LINER PAPERS (per hour)', 'Legacy variable: GLUE LINER PAPERS (per hour)', 'labor_time', 'glue_liner_papers', ARRAY['quantity_including_overs'], 1000.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '7874e198-4e9a-4ffd-9512-45c0146edbb7', 'clean_up_paper_over_board_machine', 'CLEAN UP PAPER OVER BOARD MACHINE (hours)', 'Legacy variable: CLEAN UP PAPER OVER BOARD MACHINE (hours)', 'labor_time', 'clean_up_paper_over_board_machine', NULL, 0.5, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '4646f842-7f20-42be-892d-67070f084ae2', 'set_up_creaser', 'SET UP CREASER (hours)', 'Legacy variable: SET UP CREASER (hours)', 'labor_time', 'set_up_creaser', NULL, 0.5, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '62952bb0-8a75-4842-b9cb-9719c6f02f86', 'crease', 'CREASE (per hour)', 'Legacy variable: CREASE (per hour)', 'labor_time', 'creasing_speed_8_page', ARRAY['creasing_speed_8_page', 'quantity_including_overs'], 240.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '57bd4753-ebd7-4482-b714-d1645a571e6e', 'make_ready_platten', 'MAKE READY PLATTEN (hours)', 'Legacy variable: MAKE READY PLATTEN (hours)', 'labor_time', 'make_ready_platten', NULL, 0.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a46168c1-7819-4b4e-aed3-dfeaba959d3f', 'platten_speed_in', 'PLATTEN SPEED IN (per hour)', 'Legacy variable: PLATTEN SPEED IN (per hour)', 'factory_constant', 'platten_speed_in', ARRAY['quantity_including_overs'], 360.0, 'per_hour', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '19167fc8-8ca8-4858-9739-9230293d2082', 'set_riveting_machine', 'SET RIVETING MACHINE (hours)', 'Legacy variable: SET RIVETING MACHINE (hours)', 'labor_time', 'set_riveting_machine', NULL, 0.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '267cabca-3a0d-4642-992b-6d002f747585', 'fit_2_x_corners', 'FIT 2 X CORNERS (hours)', 'Legacy variable: FIT 2 X CORNERS (hours)', 'factory_constant', 'fit_2_x_corners', ARRAY['quantity_required_by_customer'], 2.0, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '6741684e-a4f0-414d-8d3b-52da352b1b6e', 'stack_wrap_strap_per_pallet', 'STACK - WRAP - STRAP PER PALLET (hours)', 'Legacy variable: STACK - WRAP - STRAP PER PALLET (hours)', 'labor_time', 'quantity_required_by_customer/1000*0.33333', ARRAY['quantity_required_by_customer'], 2.33331, 'hours', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '567a2a25-0480-4838-858e-9e74145c63b6', 'cost_per_sheet_of_dutch_grey_board', 'COST PER SHEET OF DUTCH GREY BOARD (number)', 'Legacy variable: COST PER SHEET OF DUTCH GREY BOARD (number)', 'material_cost', 'cost_per_sheet_of_dutch_grey_board', ARRAY['quantity_including_overs', 'yield_per_sheet_of_dutch_grey_board'], 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '64e435a8-a71f-4cb7-b918-7b1e48ee2b80', 'cost_per_sheet_of_liner_paper', 'COST PER SHEET OF LINER PAPER (number)', 'Legacy variable: COST PER SHEET OF LINER PAPER (number)', 'material_cost', 'cost_per_sheet_of_liner_paper', ARRAY['quantity_including_overs', 'yield_per_sheet_from_liner_paper'], 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'c3972fc7-27bb-4770-8518-b9ef2928a24c', 'printed_and_laminated_outer_sheets', 'PRINTED AND LAMINATED OUTER SHEETS (number)', 'Legacy variable: PRINTED AND LAMINATED OUTER SHEETS (number)', 'factory_constant', 'printed_and_laminated_outer_sheets', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '02db4b1c-c39f-464e-88d1-d22de932d653', 'printed_and_laminated_inner_sheets', 'PRINTED AND LAMINATED INNER SHEETS (number)', 'Legacy variable: PRINTED AND LAMINATED INNER SHEETS (number)', 'factory_constant', 'printed_and_laminated_inner_sheets', ARRAY['quantity_including_overs'], 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'c7af7790-4cd4-49c4-8df3-897731e65aac', 'mechanism_1', 'MECHANISM (number).1', 'Legacy variable: MECHANISM (number).1', 'factory_constant', 'mechanism_1', ARRAY['quantity_required_by_customer'], 0.0, NULL, 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '74b2fcc8-02bb-44a1-bc70-b9cf8aa98ff3', 'pockets', 'POCKETS (number)', 'Legacy variable: POCKETS (number)', 'factory_constant', 'pockets', ARRAY['quantity_including_overs'], 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'bd5dfa69-d9a1-43db-a11c-96fe5243c8ad', 'digital_foil_screenprinting', 'DIGITAL/FOIL/SCREENPRINTING (number)', 'Legacy variable: DIGITAL/FOIL/SCREENPRINTING (number)', 'factory_constant', 'digital_foil_screenprinting', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '2ac47961-43ee-482c-9e58-ea94d50e035a', 'any_breakage_charges', 'ANY BREAKAGE CHARGES (number)', 'Legacy variable: ANY BREAKAGE CHARGES (number)', 'factory_constant', 'any_breakage_charges', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '85bf3b6a-0cd5-453b-8f0e-636eb1132956', 'minimum_order_carriage_charges', 'MINIMUM ORDER / CARRIAGE CHARGES (number)', 'Legacy variable: MINIMUM ORDER / CARRIAGE CHARGES (number)', 'factory_constant', 'minimum_order_carriage_charges', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a06c902b-61a1-4a8b-9981-7fdcd88963bb', 'glue_cost_per_binder', 'GLUE COST PER BINDER (number)', 'Legacy variable: GLUE COST PER BINDER (number)', 'material_cost', 'glue_cost_per_binder', ARRAY['quantity_including_overs', 'total_area_for_glue'], 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '8d6bd052-606c-4342-b3b6-78b82c3ae323', 'single_magnet_cost_gbp0_10_pence_each', 'SINGLE MAGNET COST £0.10 PENCE EACH (number)', 'Legacy variable: SINGLE MAGNET COST £0.10 PENCE EACH (number)', 'material_cost', 'single_magnet_cost_gbp0_10_pence_each', ARRAY['quantity_including_overs'], 1.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  'a0728f68-4be2-44f0-9569-2fd7aaabf9aa', 'number_of_rivets_per_binder', 'NUMBER OF RIVETS PER BINDER (number)', 'Legacy variable: NUMBER OF RIVETS PER BINDER (number)', 'calculated', 'number_of_rivets_per_binder', ARRAY['quantity_including_overs'], 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=0, customer_dep=1, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '280c1d10-5d03-4980-91f4-48d562ea3ebd', 'cutting_forme_cost_if_required', 'CUTTING FORME COST IF REQUIRED (number)', 'Legacy variable: CUTTING FORME COST IF REQUIRED (number)', 'factory_constant', 'cutting_forme_cost_if_required', NULL, 0.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

INSERT INTO pricing_rules (id, name, display_name, description, category, expression, dependencies, default_value, unit, version, is_active, notes, created_at, updated_at) VALUES (
  '5568194c-0b90-4a9c-9108-cda659900ec1', 'packing_materials_per_pallete', 'PACKING MATERIALS PER PALLETE (number)', 'Legacy variable: PACKING MATERIALS PER PALLETE (number)', 'material_cost', 'packing_materials_per_pallete', NULL, 4.0, 'units', 1, true, 'Migrated from pricing_model.csv. Flags: factory=1, customer_dep=0, customer_var=0', NOW(), NOW()
);

COMMIT;
