#!/usr/bin/env perl
use strict;
use warnings;

# Builds deterministic, biology-inspired supplementary tracks for Chr01--Chr03.
srand(20261007);
sub gaussian {
    my ($x, $center, $width) = @_;
    return exp(-(($x - $center) / $width) ** 2);
}
my @chr = qw(Chr01 Chr02 Chr03);
my (%length, %targets, %best);
open my $sizes, '<', '../rice_chromosome_sizes.tsv' or die $!;
while (<$sizes>) {
    next if /^#/;
    my ($name, undef, $end) = split /\t/;
    next unless grep { $_ eq $name } @chr;
    $length{$name} = $end;
    $targets{$name} = [map { int($end * $_) } (0.12, 0.29, 0.46, 0.63, 0.82)];
}
close $sizes;

my %accession = (Chr01 => 'NC_089035.1', Chr02 => 'NC_089036.1', Chr03 => 'NC_089037.1');
my %by_accession = reverse %accession;
open my $gtf, '<', '../../gene.gtf' or die "../../gene.gtf: $!";
while (<$gtf>) {
    next if /^#/;
    my @f = split /\t/;
    next unless @f >= 9 && $f[2] eq 'transcript' && exists $by_accession{$f[0]};
    my $name = $by_accession{$f[0]};
    my ($gene) = $f[8] =~ /gene_id\s+"([^"]+)"/;
    next unless $gene;
    for my $i (0 .. $#{$targets{$name}}) {
        my $d = abs($f[3] - $targets{$name}[$i]);
        if (!exists $best{$name}[$i] || $d < $best{$name}[$i][0]) {
            $best{$name}[$i] = [$d, $gene, $f[3], $f[4]];
        }
    }
}
close $gtf;

my @classes = qw(Yield_QTL Domestication_sweep Disease_resistance Drought_response Flowering_time);
my (%candidate, @all_candidates);
for my $name (@chr) {
    for my $i (0 .. $#{$best{$name}}) {
        my (undef, $gene, $start, $end) = @{$best{$name}[$i]};
        my $class = $classes[$i];
        $candidate{$name}[$i] = [$start, $end, $gene, $class];
        push @all_candidates, [$name, $start, $end, $gene, $class];
    }
}

# Two major association peaks only: one on Chr01 and one on Chr02.
my @major_peaks = (['Chr01', 1], ['Chr02', 3]);
open my $label_out, '>', 'peak_gene_labels.tsv' or die $!;
open my $region_out, '>', 'peak_regions.tsv' or die $!;
print {$label_out} "#Chr\tStart\tEnd\tGene_id\tPeak_class\n";
print {$region_out} "#Chr\tStart\tEnd\tPeak_class\n";
for my $peak (@major_peaks) {
    my ($name, $index) = @{$peak};
    my ($start, $end, $gene) = @{$candidate{$name}[$index]}[0, 1, 2];
    my $region_start = $start - 850_000;
    my $region_end = $end + 850_000;
    $region_start = 1 if $region_start < 1;
    $region_end = $length{$name} if $region_end > $length{$name};
    print {$label_out} join("\t", $name, $start, $end, $gene, 'Major_GWAS_peak'), "\n";
    print {$region_out} join("\t", $name, $region_start, $region_end, 'GWAS_peak_region'), "\n";
}
close $label_out;
close $region_out;

open my $gwas_out, '>', 'gwas_points.tsv' or die $!;
print {$gwas_out} "#Chr\tStart\tEnd\tNegLog10P\tAssociation_class\n";
for my $name (@chr) {
    for (1 .. 180) {
        my $pos = 1 + int(rand($length{$name}));
        my $score = 0.2 + rand() * 2.8;
        my $class = 'Background';
        printf {$gwas_out} "%s\t%d\t%d\t%.3f\t%s\n", $name, $pos, $pos, $score, $class;
    }
    for my $peak (@major_peaks) {
        next unless $peak->[0] eq $name;
        my ($start, $end) = @{$candidate{$name}[$peak->[1]]}[0, 1];
        for (1 .. 14) {
            my $pos = $start - 700_000 + int(rand(1_400_001));
            $pos = 1 if $pos < 1;
            $pos = $length{$name} if $pos > $length{$name};
            my $score = 3.3 + rand() * 2.0;
            my $class = 'Suggestive';
            printf {$gwas_out} "%s\t%d\t%d\t%.3f\t%s\n", $name, $pos, $pos, $score, $class;
        }
        my $score = 8.6 + rand() * 0.8;
        printf {$gwas_out} "%s\t%d\t%d\t%.3f\tGenome_wide\n", $name, $start, $start, $score;
    }
}
close $gwas_out;

open my $fst_out, '>', 'fst_values_200kb.tsv' or die $!;
print {$fst_out} "#Chr\tStart\tEnd\tFst\n";
for my $name (@chr) {
    for (my $start = 1, my $bin = 0; $start <= $length{$name}; $start += 200_000, ++$bin) {
        my $end = $start + 199_999;
        $end = $length{$name} if $end > $length{$name};
        my $mid = ($start + $end) / 2;
        my $fst = 0.07 + sin($bin / 6.7) * 0.025 + (rand() - 0.5) * 0.035;
        for my $peak (@major_peaks) {
            next unless $peak->[0] eq $name;
            my $peak_pos = $candidate{$name}[$peak->[1]][0];
            $fst += 0.58 * gaussian($mid, $peak_pos, 700_000);
        }
        $fst = 0.01 if $fst < 0.01;
        printf {$fst_out} "%s\t%d\t%d\t%.4f\n", $name, $start, $end, $fst;
    }
}
close $fst_out;

open my $link_out, '>', 'structural_links.tsv' or die $!;
print {$link_out} "#Chr1\tStart1\tEnd1\tVariant_type\tChr2\tStart2\tEnd2\n";
for my $name (@chr) {
    my @c = @{$candidate{$name}};
    for my $pair ([0, 2, 'Inversion'], [1, 3, 'Deletion']) {
        my ($a, $b, $type) = @{$pair};
        my ($a_start, $a_end) = ($c[$a][0] - 250_000, $c[$a][1] + 250_000);
        my ($b_start, $b_end) = ($c[$b][0] - 250_000, $c[$b][1] + 250_000);
        $a_start = 1 if $a_start < 1;
        $b_start = 1 if $b_start < 1;
        $a_end = $length{$name} if $a_end > $length{$name};
        $b_end = $length{$name} if $b_end > $length{$name};
        print {$link_out} join("\t", $name, $a_start, $a_end, $type, $name, $b_start, $b_end), "\n";
    }
}
close $link_out;

open my $pair_out, '>', 'pairwise_links.tsv' or die $!;
print {$pair_out} "#Chr\tStart\tEnd\tLD_r2\n";
for my $name (@chr) {
    my @c = @{$candidate{$name}};
    for my $pair ([0, 2, 0.86], [1, 4, 0.72], [2, 4, 0.64]) {
        my ($a, $b, $r2) = @{$pair};
        print {$pair_out} join("\t", $name, $c[$a][0], $c[$b][0], $r2), "\n";
    }
}
close $pair_out;

open my $landmark_out, '>', 'chromosome_landmarks.tsv' or die $!;
print {$landmark_out} "#Chr\tStart\tEnd\tLandmark\n";
for my $name (@chr) {
    my $len = $length{$name};
    my $cent_start = int($len * 0.43);
    my $cent_end = int($len * 0.55);
    print {$landmark_out} join("\t", $name, 1, 300_000, 'Telomere_left'), "\n";
    print {$landmark_out} join("\t", $name, $cent_start, $cent_end, 'Centromere'), "\n";
    print {$landmark_out} join("\t", $name, $len - 299_999, $len, 'Telomere_right'), "\n";
}
close $landmark_out;

print "Generated three-chromosome GWAS, gene, link and landmark tracks.\n";
